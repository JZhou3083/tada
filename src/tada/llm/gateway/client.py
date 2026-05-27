import time
import uuid
from functools import lru_cache
from typing import Sequence, TypeVar

import structlog
from google.genai import Client, types
from google.genai.errors import APIError
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from tada.llm.gateway.normalizers import (
    _normalize_contents,
    _resolve_structured_config,
    _validate_schema_model,
)
from tada.llm.gateway.retries import _is_retryable_genai_error, _log_retry
from tada.llm.gateway.telemetry import _log_and_trace_usage
from tada.settings import get_settings

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


T = TypeVar("T", bound=BaseModel)


class VertexAIGateway:
    """Small gateway around the Google GenAI client.

    Provides convenience methods for generating plain text and structured responses.
    """

    def __init__(self, client: Client):
        self.client = client

    @retry(
        retry=retry_if_exception(_is_retryable_genai_error),
        wait=wait_exponential_jitter(initial=1, max=10, jitter=0.25),
        stop=stop_after_attempt(4),
        before_sleep=_log_retry,
        reraise=True,
    )
    def _generate_content_with_retry(
        self,
        *,
        model: str,
        contents: types.ContentListUnionDict,
        config: types.GenerateContentConfigOrDict | None,
    ) -> types.GenerateContentResponse:
        """Generate content with retry handling for rate limit errors.

        Calls the Google GenAI `generate_content` API and retries only when the
        client raises a retryable `429 RESOURCE_EXHAUSTED` error. Retries use
        exponential backoff with jitter and re-raise the final exception if all
        attempts fail.

        Args:
            model: Model name or ID to use.
            contents: Normalised prompt content suitable for Google GenAI.
            config: Optional Google GenAI generation config.

        Returns:
            The raw GenAI response from `client.models.generate_content`.

        Raises:
            APIError: If the GenAI API call fails. Retryable 429 errors are
                retried before the final exception is raised.
        """
        return self.client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

    # TODO: should we implement a model fallback like previous versions?
    def generate_text(
        self,
        *,
        model: str,
        contents: types.ContentListUnionDict | Sequence[str] | str,
        config: types.GenerateContentConfigOrDict | None = None,
    ) -> str:
        """Generate a plain text response from a model.

        Retries are applied automatically for 429 RESOURCE_EXHAUSTED errors using
        exponential backoff with jitter.

        Args:
            model: Model name or ID to use.
            contents: Prompt content as a string, sequence of strings, or GenAI content object.
            config: Optional Google GenAI generation config.

        Returns:
            Tuple of the raw GenAI response and extracted response text.

        Raises:
            ValueError: If the model returns no text.
            TypeError: If `contents` is not in a supported format.
        """
        # Bind a request-scoped correlation ID so every log line within this call
        # (including any retry logs) carries the same trace token.
        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            model_name=model,
        )

        log = logger.bind(method="generate_text")
        log.info("genai.request.start")

        normalised = _normalize_contents(contents)
        t0 = time.perf_counter()

        try:
            response = self._generate_content_with_retry(
                model=model,
                contents=normalised,
                config=config,
            )

            elapsed = round(time.perf_counter() - t0, 3)

            usage = response.usage_metadata
            usage_fields = (
                {
                    "prompt_token_count": usage.prompt_token_count,
                    "cached_content_token_count": usage.cached_content_token_count,
                    "thoughts_token_count": usage.thoughts_token_count,
                    "candidates_token_count": usage.candidates_token_count,
                }
                if usage is not None
                else {}
            )

            if response.text is None:
                log.warning(
                    "genai.request.no_text", elapsed_seconds=elapsed, **usage_fields
                )
                raise ValueError(
                    "Model returned no text response. "
                    "Check whether the response was blocked, empty, or returned only non-text parts."
                )

            if usage is not None:
                _log_and_trace_usage(
                    model_name=model, usage_metadata=usage, elapsed_seconds=elapsed
                )

        except APIError as exc:
            log.error(
                "genai.request.error",
                error_type=type(exc).__name__,
                error=str(exc),
                status_code=getattr(exc, "code", None),
                elapsed_seconds=round(time.perf_counter() - t0, 3),
            )
            raise

        finally:
            structlog.contextvars.unbind_contextvars("request_id", "model_name")

        return response.text

    def generate_structured_response(
        self,
        *,
        model: str,
        contents: types.ContentListUnionDict | Sequence[str] | str,
        schema_model: type[T],
        config: types.GenerateContentConfigOrDict | None = None,
    ) -> T:
        """Generate and validate a structured response using a Pydantic model.

        The model response is requested as JSON using the schema generated from
        `schema_model`, then validated into an instance of that model.

        Retries are applied automatically for 429 RESOURCE_EXHAUSTED errors using
        exponential backoff with jitter.

        Args:
            model: Model name or ID to use.
            contents: Prompt content as a string, sequence of strings, or GenAI content object.
            schema_model: Pydantic `BaseModel` subclass defining the expected JSON response.
            config: Optional Google GenAI generation config.

        Returns:
            Tuple of the raw GenAI response and validated Pydantic model instance.

        Raises:
            TypeError: If `schema_model` is not a Pydantic `BaseModel` subclass, or if
                `contents` is not in a supported format.
            ValueError: If the model returns no text, invalid JSON, or JSON that does not
                match `schema_model`.
            ValidationError: If `config` is invalid.
        """
        _validate_schema_model(schema_model)
        log = logger.bind(
            method="generate_structured_response", schema=schema_model.__name__
        )

        resolved_config = _resolve_structured_config(
            schema_model=schema_model,
            config=config,
        )

        response_text = self.generate_text(
            model=model,
            contents=contents,
            config=resolved_config,
        )

        try:
            response_obj = schema_model.model_validate_json(response_text)
        except ValidationError as exc:
            log.error(
                "genai.structured.validation_error",
                error=str(exc),
                response_preview=response_text[:250],
            )
            raise ValueError(
                "Model returned JSON that does not match the expected schema "
                f"{schema_model.__name__}. Validation error: {exc}"
            ) from exc

        log.info("genai.structured.parsed", schema=schema_model.__name__)
        return response_obj


@lru_cache(maxsize=1)
def get_genai_client() -> Client:
    app_settings = get_settings()

    return Client(
        vertexai=True,
        project=app_settings.client_project,
        location=app_settings.client_location,
    )


@lru_cache(maxsize=1)
def get_vertexai_gateway() -> VertexAIGateway:
    return VertexAIGateway(get_genai_client())

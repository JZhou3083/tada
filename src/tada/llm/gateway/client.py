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
    normalize_contents,
    normalize_genai_usage,
    resolve_structured_config,
    validate_schema_model,
)
from tada.llm.gateway.retries import is_retryable_genai_error, log_retry
from tada.llm.gateway.telemetry import log_and_trace_usage
from tada.llm.gateway.types import GatewayResponse, ResponseMetadata
from tada.observability.cost import safe_calculate_cost
from tada.observability.cost.types import CostFailure
from tada.settings import get_settings

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


T = TypeVar("T", bound=BaseModel)


# TODO: should this gateway produce it's own spans for content generation rather than relying on auto instrumentation?
class VertexAIGateway:
    """Small gateway around the Google GenAI client.

    Provides convenience methods for generating plain text and structured responses.
    """

    def __init__(self, client: Client):
        self.client = client

    @retry(
        retry=retry_if_exception(is_retryable_genai_error),
        wait=wait_exponential_jitter(initial=1, max=10, jitter=0.25),
        stop=stop_after_attempt(4),
        before_sleep=log_retry,
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
    ) -> GatewayResponse[str]:
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
        log.info("genai.request.started", has_config=config is not None)

        normalised = normalize_contents(contents)
        t0 = time.perf_counter()

        try:
            response = self._generate_content_with_retry(
                model=model,
                contents=normalised,
                config=config,
            )

            elapsed = round(time.perf_counter() - t0, 3)

            if response.text is None:
                log.warning(
                    "genai.response.empty",
                    elapsed_seconds=elapsed,
                )
                raise ValueError(
                    "Model returned no text response. "
                    "Check whether the response was blocked, empty, or returned only non-text parts."
                )

            usage_metadata = response.usage_metadata
            token_usage = normalize_genai_usage(usage_metadata)

            if token_usage is None:
                log.warning(
                    "genai.usage.missing",
                    model_name=model,
                    elapsed_seconds=elapsed,
                )
                cost_result = CostFailure(
                    model_name=model,
                    error_type="usage_metadata_missing",
                    error_message="Model response did not include usage metadata, so cost could not be calculated.",
                )
            else:
                cost_result = safe_calculate_cost(
                    model_name=model,
                    usage=token_usage,
                )
                log_and_trace_usage(
                    model_name=model,
                    token_usage=token_usage,
                    elapsed_seconds=elapsed,
                    cost=cost_result,
                )

            response_meta = ResponseMetadata(
                request_id=request_id,
                model_name=model,
                elapsed_seconds=elapsed,
                cost=cost_result,
                input_tokens=token_usage.billable_input_tokens if token_usage else None,
                output_tokens=token_usage.billable_output_tokens
                if token_usage
                else None,
                total_tokens=token_usage.total_tokens if token_usage else None,
            )
            return GatewayResponse(content=response.text, metadata=response_meta)

        except APIError as exc:
            log.error(
                "genai.request.failed",
                error_type=type(exc).__name__,
                error=str(exc),
                status_code=getattr(exc, "code", None),
                elapsed_seconds=round(time.perf_counter() - t0, 3),
            )
            raise

        finally:
            structlog.contextvars.unbind_contextvars("request_id", "model_name")

    def generate_structured_response(
        self,
        *,
        model: str,
        contents: types.ContentListUnionDict | Sequence[str] | str,
        schema_model: type[T],
        config: types.GenerateContentConfigOrDict | None = None,
    ) -> GatewayResponse[T]:
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
        validate_schema_model(schema_model)
        log = logger.bind(
            method="generate_structured_response", schema=schema_model.__name__
        )

        resolved_config = resolve_structured_config(
            schema_model=schema_model,
            config=config,
        )

        text_response = self.generate_text(
            model=model,
            contents=contents,
            config=resolved_config,
        )

        try:
            response_obj = schema_model.model_validate_json(text_response.content)
        except ValidationError as exc:
            log.error(
                "genai.structured.validation_failed",
                request_id=text_response.metadata.request_id,
                schema=schema_model.__name__,
                error_type=type(exc).__name__,
                error=str(exc),
                response_preview=text_response.content[:250],
            )
            raise ValueError(
                "Model returned JSON that does not match the expected schema "
                f"{schema_model.__name__}. Validation error: {exc}"
            ) from exc

        log.info(
            "genai.structured.parsed",
            request_id=text_response.metadata.request_id,
            model_name=model,
            schema=schema_model.__name__,
        )
        return GatewayResponse(content=response_obj, metadata=text_response.metadata)


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

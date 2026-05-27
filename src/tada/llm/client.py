import time
import uuid
from functools import lru_cache
from typing import Any, Sequence, TypeVar

import structlog
from google.genai import Client, types
from google.genai.errors import APIError
from opentelemetry import trace
from pydantic import BaseModel, ValidationError
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from tada.observability.cost.calculator import safe_calculate_cost
from tada.observability.cost.types import CostSuccess

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def cost_to_observability_fields(result: CostSuccess) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "llm.model_name": result.model_name,
        "llm.cost.total_usd": str(result.total_cost_usd),
    }

    for component in result.breakdown:
        fields[f"llm.token_count.{component.name}"] = component.tokens
        fields[f"llm.cost.{component.name}_usd"] = str(component.cost_usd)

    return fields


def _log_llm_usage(
    model_name: str,
    usage_metadata: types.GenerateContentResponseUsageMetadata,
    elapsed_seconds: float,
) -> None:
    fields: dict[str, Any] = {
        "llm.model": model_name,
        "llm.response.elapsed_seconds": elapsed_seconds,
    }

    cost = safe_calculate_cost(
        model_name=model_name,
        usage={
            "prompt_token_count": usage_metadata.prompt_token_count,
            "cached_content_token_count": usage_metadata.cached_content_token_count,
            "thoughts_token_count": usage_metadata.thoughts_token_count,
            "candidates_token_count": usage_metadata.candidates_token_count,
        },
    )

    if isinstance(cost, CostSuccess):
        fields = {
            **cost_to_observability_fields(cost),
        }
    else:
        fields = {
            "llm.cost.error.type": cost.error_type,
            "llm.cost.error.message": cost.error_message,
        }

    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in fields.items():
            if value is not None:
                span.set_attribute(key, value)

    logger.info("genai.request.usage", **fields)


# ------------------------
# Tenacity retries
# ------------------------


def _log_retry(retry_state: RetryCallState) -> None:
    """Structured log emitted by tenacity before each sleep between retries."""
    # .outcome & .next_action are guaranteed at call time, but we guard in-line with type-checkers.
    exc = retry_state.outcome.exception() if retry_state.outcome is not None else None
    wait = (
        round(retry_state.next_action.sleep, 2)
        if retry_state.next_action is not None
        else None
    )
    logger.warning(
        "genai.retry",
        attempt=retry_state.attempt_number,
        wait_seconds=wait,
        total_idle_seconds=round(retry_state.idle_for, 2),
        error_type=type(exc).__name__,
        error=str(exc),
    )


def _is_retryable_genai_error(exc: BaseException) -> bool:
    """Return whether a GenAI exception should be retried.

    Retries are limited to Google GenAI API errors with status code `429`, which
    indicates `RESOURCE_EXHAUSTED` / rate limiting.
    """
    if not isinstance(exc, APIError):
        return False

    code = getattr(exc, "code", None)
    return code == 429


# ------------------------
# Contents handling
# ------------------------


def _contents_from_text_parts(text_parts: Sequence[str]) -> types.Content:
    """Create a user content object from one or more text parts.

    Args:
        text_parts: Non-empty sequence of text strings to send as user input.

    Returns:
        A Google GenAI `Content` object with role set to `"user"`.

    Raises:
        ValueError: If `text_parts` is empty or contains empty strings.
    """
    if not text_parts:
        raise ValueError("text_parts must contain at least one string")

    empty_indexes = [idx for idx, part in enumerate(text_parts) if not part.strip()]
    if empty_indexes:
        raise ValueError(
            "text_parts must not contain empty or whitespace-only strings; "
            f"invalid indexes: {empty_indexes}"
        )

    return types.Content(
        role="user",
        parts=[types.Part.from_text(text=part) for part in text_parts],
    )


def _normalize_contents(
    contents: types.ContentListUnionDict | Sequence[str] | str,
) -> types.ContentListUnionDict:
    """Normalise supported prompt inputs into Google GenAI content format.

    Supported inputs:
    - `str`: converted into a single user text part
    - `Sequence[str]`: converted into multiple user text parts
    - Google GenAI content object/dict: returned unchanged

    Args:
        contents: Prompt content in one of the supported formats.

    Returns:
        A value suitable for `client.models.generate_content(contents=...)`.

    Raises:
        TypeError: If a sequence contains non-string values.
        ValueError: If a string or string sequence is empty.
    """
    if isinstance(contents, str):
        if not contents.strip():
            raise ValueError("contents must not be an empty or whitespace-only string")

        return _contents_from_text_parts([contents])

    if isinstance(contents, Sequence) and not isinstance(contents, (str, bytes)):
        non_string_items = [
            (idx, type(part).__name__)
            for idx, part in enumerate(contents)
            if not isinstance(part, str)
        ]

        if non_string_items:
            raise TypeError(
                "contents must be a string, a sequence of strings, "
                "or a valid Google GenAI contents object. "
                f"Found non-string sequence items: {non_string_items}"
            )

        return _contents_from_text_parts(contents)

    return contents


# ------------------------
# Config handling
# ------------------------


def _coerce_config(
    config: types.GenerateContentConfigOrDict,
) -> types.GenerateContentConfig:
    """Convert a config dict into a `GenerateContentConfig` instance if needed.

    Args:
        config: Existing GenAI config object or compatible dictionary.

    Returns:
        A validated `GenerateContentConfig` instance.

    Raises:
        ValidationError: If a dictionary config is not valid.
    """
    if isinstance(config, types.GenerateContentConfig):
        return config

    return types.GenerateContentConfig.model_validate(config)


def _validate_schema_model(schema_model: object) -> None:
    """Validate that an object is a Pydantic model class.

    Args:
        schema_model: Object expected to be a subclass of `pydantic.BaseModel`.

    Raises:
        TypeError: If `schema_model` is not a class, or if it is not a subclass
            of `pydantic.BaseModel`.
    """
    if not isinstance(schema_model, type) or not issubclass(schema_model, BaseModel):
        raise TypeError(
            "schema_model must be a subclass of pydantic.BaseModel, "
            f"got {schema_model!r} (type={type(schema_model).__name__})"
        )


def _resolve_structured_config(
    schema_model: type[BaseModel],
    config: types.GenerateContentConfigOrDict | None,
) -> types.GenerateContentConfig:
    """Create a generation config for structured JSON responses.

    The returned config requests a JSON response and applies the JSON schema
    generated from the provided Pydantic model.

    Args:
        schema_model: Pydantic `BaseModel` subclass defining the expected response schema.
        config: Optional base Google GenAI generation config or compatible dictionary.

    Returns:
        A `GenerateContentConfig` configured for JSON structured output.

    Raises:
        ValidationError: If `config` is a dictionary that cannot be validated as a
            `GenerateContentConfig`.
    """
    base_config = (
        types.GenerateContentConfig() if config is None else _coerce_config(config)
    )

    return base_config.model_copy(
        update={
            "response_mime_type": "application/json",
            "response_json_schema": schema_model.model_json_schema(),
        }
    )


# ------------------------
# Gateway
# ------------------------

T = TypeVar("T", bound=BaseModel)


# TODO: can cost reporting be done here - thus saving the need for logic in the graph and no need to return the full response obj
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
    ) -> tuple[types.GenerateContentResponse, str]:
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
            model=model,
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
            # usage_metadata is None if the response doesn't include token counts
            usage = response.usage_metadata

            usage_fields = {
                "prompt_token_count": getattr(usage, "prompt_token_count", None),
                "candidates_token_count": getattr(
                    usage, "candidates_token_count", None
                ),
                "cached_content_token_count": getattr(
                    usage, "cached_content_token_count", None
                ),
                "thoughts_token_count": getattr(usage, "thoughts_token_count", None),
                "total_token_count": getattr(usage, "total_token_count", None),
            }

            if response.text is None:
                log.warning(
                    "genai.request.no_text", elapsed_seconds=elapsed, **usage_fields
                )
                raise ValueError(
                    "Model returned no text response. "
                    "Check whether the response was blocked, empty, or returned only non-text parts."
                )

            log.info(
                "genai.request.complete",
                elapsed_seconds=elapsed,
                **usage_fields,
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
            structlog.contextvars.unbind_contextvars("request_id", "model")

        return response, response.text

    def generate_structured_response(
        self,
        *,
        model: str,
        contents: types.ContentListUnionDict | Sequence[str] | str,
        schema_model: type[T],
        config: types.GenerateContentConfigOrDict | None = None,
    ) -> tuple[types.GenerateContentResponse, T]:
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

        response, response_text = self.generate_text(
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
        except ValueError as exc:
            log.error(
                "genai.structured.invalid_json",
                error=str(exc),
                response_preview=response_text[:250],
            )
            raise ValueError(
                "Model returned invalid JSON for expected schema "
                f"{schema_model.__name__}. Response text starts with: "
                f"{response_text[:250]!r}"
            ) from exc

        log.info("genai.structured.parsed", schema=schema_model.__name__)
        return response, response_obj


@lru_cache(maxsize=1)
def get_genai_client() -> Client:
    return Client(
        vertexai=True,
        project="jlr-dl-cat",
        location="global",
    )


@lru_cache(maxsize=1)
def get_vertexai_gateway() -> VertexAIGateway:
    return VertexAIGateway(get_genai_client())

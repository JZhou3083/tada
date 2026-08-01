import json
import time
import uuid
from functools import lru_cache
from typing import Sequence, TypeVar

import structlog
from google.genai import Client, types
from google.genai.errors import APIError
from pydantic import BaseModel

from tada.llm.configs import GenerationConfig
from tada.llm.gateway.base import (
    ContentsInput,
    validate_schema_model,
    validate_structured_payload,
)
from tada.llm.gateway.retries import with_retry
from tada.llm.gateway.telemetry import log_and_trace_usage
from tada.llm.gateway.types import GatewayResponse, ResponseMetadata
from tada.observability.cost import safe_calculate_cost
from tada.observability.cost.types import CostFailure, LLMTokenUsage

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


def is_retryable_genai_error(exc: BaseException) -> bool:
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
        parts=[types.Part.from_text(text=part) for part in text_parts],
        role="user",
    )


def _normalize_contents(contents: ContentsInput) -> types.ContentListUnionDict:
    """Normalise supported prompt inputs into Google GenAI content format.

    Supported inputs:
    - `str`: converted into a single user text part
    - `Sequence[str]`: converted into multiple user text parts

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

    non_string_items = [
        (idx, type(part).__name__)
        for idx, part in enumerate(contents)
        if not isinstance(part, str)
    ]

    if non_string_items:
        raise TypeError(
            "contents must be a string or a sequence of strings. "
            f"Found non-string sequence items: {non_string_items}"
        )

    return _contents_from_text_parts(contents)


# ------------------------
# Usage observability
# ------------------------


def _normalize_genai_usage(
    usage_metadata: types.GenerateContentResponseUsageMetadata | None,
) -> LLMTokenUsage | None:
    if usage_metadata is None:
        return None

    return LLMTokenUsage(
        input_tokens=usage_metadata.prompt_token_count,
        cached_input_tokens=usage_metadata.cached_content_token_count,
        thoughts_tokens=usage_metadata.thoughts_token_count,
        output_tokens=usage_metadata.candidates_token_count,
    )


# ------------------------
# Config handling
# ------------------------


def _build_generate_content_config(
    config: GenerationConfig | None,
    *,
    response_json_schema: dict | None = None,
) -> types.GenerateContentConfig:
    config = config or GenerationConfig()

    kwargs: dict = dict(
        system_instruction=config.system_instruction,
        temperature=config.temperature,
        top_p=config.top_p,
        seed=config.seed,
        max_output_tokens=config.max_output_tokens,
        candidate_count=1,
        labels=config.labels or None,
    )

    if response_json_schema is not None:
        kwargs["response_mime_type"] = "application/json"
        kwargs["response_json_schema"] = response_json_schema

    return types.GenerateContentConfig(**kwargs)


# TODO: should this gateway produce it's own spans for content generation rather than relying on auto instrumentation?
class GoogleVertexGateway:
    """Gateway around the Google GenAI (Vertex AI) client.

    Provides convenience methods for generating plain text and structured responses.
    """

    def __init__(self, client: Client):
        self.client = client

    @with_retry(is_retryable_genai_error)
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
        """
        return self.client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

    def _generate(
        self,
        *,
        model: str,
        contents: ContentsInput,
        config: types.GenerateContentConfig,
    ) -> GatewayResponse[str]:
        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            model_name=model,
        )

        log = logger.bind(method="generate")
        log.info("genai.request.started", has_config=config is not None)

        normalised = _normalize_contents(contents)
        t0 = time.perf_counter()

        try:
            response = self._generate_content_with_retry(
                model=model,
                contents=normalised,
                config=config,
            )

            elapsed = round(time.perf_counter() - t0, 3)

            if response.text is None:
                log.warning("genai.response.empty", elapsed_seconds=elapsed)
                raise ValueError(
                    "Model returned no text response. "
                    "Check whether the response was blocked, empty, or returned only non-text parts."
                )

            usage_metadata = response.usage_metadata
            token_usage = _normalize_genai_usage(usage_metadata)

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
                cost_result = safe_calculate_cost(model_name=model, usage=token_usage)
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

    def generate_text(
        self,
        *,
        model: str,
        contents: ContentsInput,
        config: GenerationConfig | None = None,
    ) -> GatewayResponse[str]:
        """Generate a plain text response from a model.

        Retries are applied automatically for 429 RESOURCE_EXHAUSTED errors using
        exponential backoff with jitter.

        Raises:
            ValueError: If the model returns no text.
            TypeError: If `contents` is not in a supported format.
        """
        return self._generate(
            model=model,
            contents=contents,
            config=_build_generate_content_config(config),
        )

    def generate_structured_response(
        self,
        *,
        model: str,
        contents: ContentsInput,
        schema_model: type[T],
        config: GenerationConfig | None = None,
    ) -> GatewayResponse[T]:
        """Generate and validate a structured response using a Pydantic model.

        The model response is requested as JSON using the schema generated from
        `schema_model`, then validated into an instance of that model.

        Raises:
            TypeError: If `schema_model` is not a Pydantic `BaseModel` subclass, or if
                `contents` is not in a supported format.
            ValueError: If the model returns no text, invalid JSON, or JSON that does not
                match `schema_model`.
        """
        validate_schema_model(schema_model)

        text_response = self._generate(
            model=model,
            contents=contents,
            config=_build_generate_content_config(
                config, response_json_schema=schema_model.model_json_schema()
            ),
        )

        try:
            payload = json.loads(text_response.content)
        except json.JSONDecodeError as exc:
            logger.error(
                "genai.structured.invalid_json",
                request_id=text_response.metadata.request_id,
                schema=schema_model.__name__,
                error=str(exc),
                response_preview=text_response.content[:250],
            )
            raise ValueError(
                f"Model returned invalid JSON for schema {schema_model.__name__}: {exc}"
            ) from exc

        parsed = validate_structured_payload(
            payload,
            schema_model,
            request_id=text_response.metadata.request_id,
        )

        logger.info(
            "genai.structured.parsed",
            request_id=text_response.metadata.request_id,
            model_name=model,
            schema=schema_model.__name__,
        )
        return GatewayResponse(content=parsed, metadata=text_response.metadata)


@lru_cache(maxsize=1)
def get_genai_client(project: str, location: str) -> Client:
    return Client(
        vertexai=True,
        project=project,
        location=location,
    )


@lru_cache(maxsize=1)
def get_google_vertex_gateway(project: str, location: str) -> GoogleVertexGateway:
    return GoogleVertexGateway(get_genai_client(project, location))

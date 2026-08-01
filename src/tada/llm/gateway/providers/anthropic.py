import time
import uuid
from functools import lru_cache
from typing import TypeVar

import structlog
from anthropic import Anthropic, APIError, RateLimitError
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

# Anthropic has no JSON mode, so structured responses are extracted via a
# forced tool-use call to this synthetic tool instead.
_STRUCTURED_TOOL_NAME = "emit_result"


def is_retryable_anthropic_error(exc: BaseException) -> bool:
    """Return whether an Anthropic exception should be retried.

    Retries are limited to `429` rate-limit errors, matching the retry scope
    used for the other provider adapters.
    """
    return isinstance(exc, RateLimitError)


def _content_from_contents(contents: ContentsInput) -> str:
    """Join prompt content into a single user-message string.

    Supported inputs:
    - `str`: used as-is
    - `Sequence[str]`: joined together

    Raises:
        ValueError: If `contents` is empty or contains empty strings.
    """
    parts = [contents] if isinstance(contents, str) else list(contents)

    if not parts:
        raise ValueError("contents must contain at least one string")

    empty_indexes = [idx for idx, part in enumerate(parts) if not part.strip()]
    if empty_indexes:
        raise ValueError(
            "contents must not contain empty or whitespace-only strings; "
            f"invalid indexes: {empty_indexes}"
        )

    return "\n\n".join(parts)


class AnthropicGateway:
    """Gateway around the Anthropic Messages API.

    Anthropic has no dedicated JSON-mode, so `generate_structured_response`
    forces the model to call a synthetic `emit_result` tool whose input schema
    is the target Pydantic model's JSON schema, then reads the parsed input
    off the resulting `tool_use` content block.
    """

    def __init__(self, client: Anthropic):
        self.client = client

    @with_retry(is_retryable_anthropic_error)
    def _create_with_retry(self, **kwargs):
        return self.client.messages.create(**kwargs)

    def _base_kwargs(
        self,
        *,
        model: str,
        contents: ContentsInput,
        config: GenerationConfig | None,
    ) -> dict:
        config = config or GenerationConfig()
        kwargs: dict = dict(
            model=model,
            max_tokens=config.max_output_tokens,
            temperature=config.temperature,
            top_p=config.top_p,
            messages=[{"role": "user", "content": _content_from_contents(contents)}],
        )
        if config.system_instruction:
            kwargs["system"] = config.system_instruction
        return kwargs

    def _build_metadata(
        self,
        *,
        request_id: str,
        model: str,
        elapsed: float,
        usage,
    ) -> ResponseMetadata:
        token_usage = (
            LLMTokenUsage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cached_input_tokens=getattr(usage, "cache_read_input_tokens", None),
            )
            if usage is not None
            else None
        )

        if token_usage is None:
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

        return ResponseMetadata(
            request_id=request_id,
            model_name=model,
            elapsed_seconds=elapsed,
            cost=cost_result,
            input_tokens=token_usage.billable_input_tokens if token_usage else None,
            output_tokens=token_usage.billable_output_tokens if token_usage else None,
            total_tokens=token_usage.total_tokens if token_usage else None,
        )

    def generate_text(
        self,
        *,
        model: str,
        contents: ContentsInput,
        config: GenerationConfig | None = None,
    ) -> GatewayResponse[str]:
        """Generate a plain text response from a model.

        Raises:
            ValueError: If the model returns no text.
        """
        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id, model_name=model)
        log = logger.bind(method="generate_text")
        log.info("anthropic.request.started")

        t0 = time.perf_counter()
        try:
            response = self._create_with_retry(
                **self._base_kwargs(model=model, contents=contents, config=config)
            )
            elapsed = round(time.perf_counter() - t0, 3)

            text_blocks = [
                block.text for block in response.content if block.type == "text"
            ]
            if not text_blocks:
                log.warning("anthropic.response.empty", elapsed_seconds=elapsed)
                raise ValueError(
                    "Model returned no text response. "
                    "Check whether the response was blocked, empty, or returned only non-text parts."
                )

            metadata = self._build_metadata(
                request_id=request_id, model=model, elapsed=elapsed, usage=response.usage
            )
            return GatewayResponse(content="".join(text_blocks), metadata=metadata)

        except APIError as exc:
            log.error(
                "anthropic.request.failed",
                error_type=type(exc).__name__,
                error=str(exc),
                status_code=getattr(exc, "status_code", None),
                elapsed_seconds=round(time.perf_counter() - t0, 3),
            )
            raise

        finally:
            structlog.contextvars.unbind_contextvars("request_id", "model_name")

    def generate_structured_response(
        self,
        *,
        model: str,
        contents: ContentsInput,
        schema_model: type[T],
        config: GenerationConfig | None = None,
    ) -> GatewayResponse[T]:
        """Generate and validate a structured response using forced tool-use.

        Raises:
            TypeError: If `schema_model` is not a Pydantic `BaseModel` subclass.
            ValueError: If the model does not call the forced tool, or the tool
                input does not match `schema_model`.
        """
        validate_schema_model(schema_model)

        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id, model_name=model)
        log = logger.bind(
            method="generate_structured_response", schema=schema_model.__name__
        )
        log.info("anthropic.request.started", forced_tool=_STRUCTURED_TOOL_NAME)

        kwargs = self._base_kwargs(model=model, contents=contents, config=config)
        kwargs["tools"] = [
            {
                "name": _STRUCTURED_TOOL_NAME,
                "description": f"Emit the result as a {schema_model.__name__} JSON object.",
                "input_schema": schema_model.model_json_schema(),
            }
        ]
        kwargs["tool_choice"] = {"type": "tool", "name": _STRUCTURED_TOOL_NAME}

        t0 = time.perf_counter()
        try:
            response = self._create_with_retry(**kwargs)
            elapsed = round(time.perf_counter() - t0, 3)

            tool_use_blocks = [
                block
                for block in response.content
                if block.type == "tool_use" and block.name == _STRUCTURED_TOOL_NAME
            ]
            if not tool_use_blocks:
                log.warning("anthropic.response.no_tool_use", elapsed_seconds=elapsed)
                raise ValueError(
                    f"Model did not call the forced '{_STRUCTURED_TOOL_NAME}' tool; "
                    "cannot extract a structured response."
                )

            payload = tool_use_blocks[0].input
            metadata = self._build_metadata(
                request_id=request_id, model=model, elapsed=elapsed, usage=response.usage
            )

        except APIError as exc:
            log.error(
                "anthropic.request.failed",
                error_type=type(exc).__name__,
                error=str(exc),
                status_code=getattr(exc, "status_code", None),
                elapsed_seconds=round(time.perf_counter() - t0, 3),
            )
            raise

        finally:
            structlog.contextvars.unbind_contextvars("request_id", "model_name")

        parsed = validate_structured_payload(payload, schema_model, request_id=request_id)

        log.info(
            "anthropic.structured.parsed",
            request_id=request_id,
            model_name=model,
            schema=schema_model.__name__,
        )
        return GatewayResponse(content=parsed, metadata=metadata)


@lru_cache(maxsize=1)
def get_anthropic_gateway(api_key: str) -> AnthropicGateway:
    return AnthropicGateway(Anthropic(api_key=api_key))

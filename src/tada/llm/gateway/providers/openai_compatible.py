import json
import time
import uuid
from functools import lru_cache
from typing import TypeVar

import structlog
from openai import APIError, OpenAI, RateLimitError
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


def is_retryable_openai_error(exc: BaseException) -> bool:
    """Return whether an OpenAI-compatible exception should be retried.

    Retries are limited to `429` rate-limit errors, matching the retry scope
    used for the other provider adapters.
    """
    return isinstance(exc, RateLimitError)


def _messages_from_contents(
    contents: ContentsInput,
    *,
    system_instruction: str | None,
) -> list[dict[str, str]]:
    """Build a Chat Completions `messages` list from prompt content.

    Supported inputs:
    - `str`: sent as a single user message
    - `Sequence[str]`: joined into a single user message

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

    messages: list[dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": "\n\n".join(parts)})
    return messages


class OpenAIGateway:
    """Gateway around an OpenAI-compatible Chat Completions API.

    Used directly for OpenAI. Also reused for DeepSeek, an OpenAI-compatible
    endpoint with weaker structured-output support (no strict JSON-schema mode),
    via `supports_json_schema=False`.
    """

    def __init__(
        self,
        client: OpenAI,
        *,
        supports_json_schema: bool = True,
        disable_thinking: bool = False,
        structured_reasoning_effort: str | None = None,
    ):
        self.client = client
        self.supports_json_schema = supports_json_schema
        # DeepSeek's v4 models default to an extended internal reasoning pass (at
        # "high" effort) whose tokens count against `max_tokens` alongside the
        # actual answer. For free-form section-doc generation (large prompt, long
        # prose output), even `reasoning_effort="low"` was observed in practice to
        # still occasionally consume the entire `max_tokens` budget on reasoning
        # alone, leaving an empty `content` — so generation disables thinking
        # outright via `disable_thinking` rather than merely capping its effort.
        self.disable_thinking = disable_thinking
        # Structured calls (e.g. section-doc evaluation) have a small, bounded JSON
        # output, so there's little risk of reasoning alone exhausting the budget —
        # and that task genuinely benefits from multi-step reasoning (the eval
        # prompt asks for step-by-step comparison), so it's capped via
        # `reasoning_effort` rather than disabled entirely.
        self.structured_reasoning_effort = structured_reasoning_effort

    @with_retry(is_retryable_openai_error)
    def _create_with_retry(self, **kwargs):
        return self.client.chat.completions.create(**kwargs)

    def _generate(
        self,
        *,
        model: str,
        contents: ContentsInput,
        config: GenerationConfig | None,
        response_format: dict | None = None,
        disable_thinking: bool = False,
        reasoning_effort: str | None = None,
    ) -> GatewayResponse[str]:
        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id, model_name=model)

        log = logger.bind(method="generate")
        log.info("openai.request.started", has_response_format=response_format is not None)

        config = config or GenerationConfig()
        messages = _messages_from_contents(
            contents, system_instruction=config.system_instruction
        )

        t0 = time.perf_counter()
        try:
            create_kwargs: dict = dict(
                model=model,
                messages=messages,
                temperature=config.temperature,
                top_p=config.top_p,
                seed=config.seed,
                max_tokens=config.max_output_tokens,
            )
            if response_format is not None:
                create_kwargs["response_format"] = response_format
            if disable_thinking:
                create_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
            elif reasoning_effort is not None:
                create_kwargs["reasoning_effort"] = reasoning_effort

            response = self._create_with_retry(**create_kwargs)
            elapsed = round(time.perf_counter() - t0, 3)

            content = response.choices[0].message.content
            if content is None:
                log.warning("openai.response.empty", elapsed_seconds=elapsed)
                raise ValueError(
                    "Model returned no text response. "
                    "Check whether the response was blocked, empty, or returned only non-text parts."
                )

            usage = response.usage
            token_usage = (
                LLMTokenUsage(
                    input_tokens=usage.prompt_tokens,
                    output_tokens=usage.completion_tokens,
                    cached_input_tokens=(
                        usage.prompt_tokens_details.cached_tokens
                        if usage.prompt_tokens_details is not None
                        else None
                    ),
                )
                if usage is not None
                else None
            )

            if token_usage is None:
                log.warning("openai.usage.missing", model_name=model, elapsed_seconds=elapsed)
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
            return GatewayResponse(content=content, metadata=response_meta)

        except APIError as exc:
            log.error(
                "openai.request.failed",
                error_type=type(exc).__name__,
                error=str(exc),
                status_code=getattr(exc, "status_code", None),
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

        Raises:
            ValueError: If the model returns no text.
        """
        return self._generate(
            model=model,
            contents=contents,
            config=config,
            disable_thinking=self.disable_thinking,
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

        On an endpoint that supports strict JSON-schema mode (`supports_json_schema=True`,
        i.e. OpenAI proper), the schema is enforced by the API itself. Otherwise
        (DeepSeek), only the weaker `json_object` mode is requested and the schema
        is appended to the prompt as an instruction instead, since the API can't
        enforce it directly.

        Raises:
            TypeError: If `schema_model` is not a Pydantic `BaseModel` subclass.
            ValueError: If the model returns no text, invalid JSON, or JSON that does
                not match `schema_model`.
        """
        validate_schema_model(schema_model)
        schema = schema_model.model_json_schema()

        if self.supports_json_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_model.__name__,
                    "schema": schema,
                    "strict": True,
                },
            }
            text_response = self._generate(
                model=model,
                contents=contents,
                config=config,
                response_format=response_format,
                reasoning_effort=self.structured_reasoning_effort,
            )
        else:
            schema_instruction = (
                "Respond only with a single JSON object matching this JSON Schema "
                f"(no surrounding prose or markdown fences):\n{json.dumps(schema)}"
            )
            augmented_contents = (
                [contents, schema_instruction]
                if isinstance(contents, str)
                else [*contents, schema_instruction]
            )
            text_response = self._generate(
                model=model,
                contents=augmented_contents,
                config=config,
                response_format={"type": "json_object"},
                reasoning_effort=self.structured_reasoning_effort,
            )

        try:
            payload = json.loads(text_response.content)
        except json.JSONDecodeError as exc:
            logger.error(
                "openai.structured.invalid_json",
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
            "openai.structured.parsed",
            request_id=text_response.metadata.request_id,
            model_name=model,
            schema=schema_model.__name__,
        )
        return GatewayResponse(content=parsed, metadata=text_response.metadata)


@lru_cache(maxsize=1)
def get_openai_gateway(api_key: str) -> OpenAIGateway:
    return OpenAIGateway(OpenAI(api_key=api_key), supports_json_schema=True)


@lru_cache(maxsize=1)
def get_deepseek_gateway(api_key: str, base_url: str) -> OpenAIGateway:
    return OpenAIGateway(
        OpenAI(api_key=api_key, base_url=base_url),
        supports_json_schema=False,
        disable_thinking=False,
        structured_reasoning_effort="low",
    )

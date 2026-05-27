from typing import Any

import structlog
from google.genai import types
from opentelemetry import trace

from tada.observability.cost.calculator import safe_calculate_cost
from tada.observability.cost.types import CostResult, CostSuccess

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def _build_cost_fields(result: CostResult) -> dict[str, Any]:
    """Map a cost result to OpenInference-compatible span fields."""
    if isinstance(result, CostSuccess):
        fields: dict[str, Any] = {
            "llm.cost.total_usd": str(result.total_cost_usd),
        }
        for component in result.breakdown:
            fields[f"llm.token_count.{component.name}"] = component.tokens
            fields[f"llm.cost.{component.name}_usd"] = str(component.cost_usd)
        return fields

    return {
        "llm.cost.error.type": result.error_type,
        "llm.cost.error.message": result.error_message,
    }


def _log_and_trace_usage(
    model_name: str,
    usage_metadata: types.GenerateContentResponseUsageMetadata,
    elapsed_seconds: float,
) -> None:
    cost = safe_calculate_cost(
        model_name=model_name,
        usage={
            "prompt_token_count": usage_metadata.prompt_token_count,
            "cached_content_token_count": usage_metadata.cached_content_token_count,
            "thoughts_token_count": usage_metadata.thoughts_token_count,
            "candidates_token_count": usage_metadata.candidates_token_count,
        },
    )

    fields: dict[str, Any] = {
        "llm.model": model_name,
        "llm.response.elapsed_seconds": elapsed_seconds,
        "llm.token_count.total": usage_metadata.total_token_count,
        **_build_cost_fields(cost),
    }

    span = trace.get_current_span()
    if span.is_recording():
        for key, value in fields.items():
            if value is not None:
                span.set_attribute(key, value)

    logger.info("genai.request.complete", **fields)

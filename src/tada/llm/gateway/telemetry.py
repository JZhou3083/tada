from typing import Any

import structlog
from opentelemetry import trace

from tada.observability.cost.calculator import safe_calculate_cost
from tada.observability.cost.types import CostResult, CostSuccess, LLMTokenUsage

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


def log_and_trace_usage(
    model_name: str,
    token_usage: LLMTokenUsage,
    elapsed_seconds: float,
    cost: CostResult | None = None,
) -> None:
    if cost is None:
        cost = safe_calculate_cost(model_name=model_name, usage=token_usage)

    fields: dict[str, Any] = {
        "llm.model": model_name,
        "llm.response.elapsed_seconds": elapsed_seconds,
        "llm.token_count.total": token_usage.total_tokens,
        **_build_cost_fields(cost),
    }

    span = trace.get_current_span()
    if span.is_recording():
        for key, value in fields.items():
            if value is not None:
                span.set_attribute(key, value)

    logger.info("genai.request.complete", **fields)

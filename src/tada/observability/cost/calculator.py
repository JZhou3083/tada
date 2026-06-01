from __future__ import annotations

from decimal import Decimal
from typing import Callable

import structlog

from tada.observability.cost.errors import (
    CostError,
    PricingNotFoundError,
)
from tada.observability.cost.pricing import load_pricing_config
from tada.observability.cost.schemas import ModelPricing, PricingConfig
from tada.observability.cost.types import (
    CostComponent,
    CostFailure,
    CostResult,
    CostSuccess,
    LLMTokenUsage,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

TokenCounter = Callable[[LLMTokenUsage], int]
RateGetter = Callable[[ModelPricing], Decimal | None]

COST_COMPONENTS: tuple[tuple[str, TokenCounter, RateGetter], ...] = (
    (
        "cached_input",
        lambda usage: usage.billable_cached_input_tokens,
        lambda pricing: (
            pricing.cached_input_cost_per_1m or pricing.input_cost_per_1m
        ),  # if cached input cost is not provided, fall back to regular input cost
    ),
    (
        "input",
        lambda usage: usage.billable_input_tokens,
        lambda pricing: pricing.input_cost_per_1m,
    ),
    (
        "thoughts",
        lambda usage: usage.billable_thoughts_tokens,
        lambda pricing: pricing.thoughts_cost_per_1m,
    ),
    (
        "output",
        lambda usage: usage.billable_output_tokens,
        lambda pricing: pricing.output_cost_per_1m,
    ),
)


def _calculate_component_cost(
    tokens: int,
    rate_per_1m: Decimal | None,
) -> Decimal:
    """Calculate the USD cost for a token component using a per-1M token rate."""
    if not tokens or rate_per_1m is None:
        return Decimal("0")

    return Decimal(tokens) * rate_per_1m / Decimal("1000000")


def calculate_cost(
    model_name: str,
    usage: LLMTokenUsage,
    *,
    pricing_config: PricingConfig | None = None,
) -> CostSuccess:
    """
    Calculate the estimated USD cost for a model usage record.

    Args:
        model_name: Model name reported by the provider.
        usage: Token usage metrics for the request.

    Expected usage keys:
        prompt_token_count: Total prompt/input tokens.
        cached_content_token_count: Prompt tokens served from cache.
        thoughts_token_count: Internal reasoning/thinking tokens, if reported.
        candidates_token_count: Output/completion tokens.

    Returns:
        A CostSuccess dataclass containing the model name, per-component cost breakdown,
        and total estimated cost in USD.

    Notes:
        - Non-essential individual token fields (thoughts/cached input) are treated as zero if missing.
        - Missing input/output token fields will result in an invalid usage error.
        - Missing usage metadata as a whole (empty payload) is treated as unknown and returns a missing usage error.
        - Input cost excludes cached input tokens.
    """
    logger.debug(
        "cost.calculation.started",
        model_name=model_name,
    )

    if pricing_config is None:
        pricing_config = load_pricing_config()

    if model_name not in pricing_config.pricing:
        raise PricingNotFoundError(f"No pricing found for model: {model_name!r}")

    model_pricing = pricing_config.pricing[model_name]

    breakdown: list[CostComponent] = []
    for component_name, token_counter, rate_getter in COST_COMPONENTS:
        tokens = token_counter(usage)
        rate = rate_getter(model_pricing)
        cost_usd = _calculate_component_cost(tokens, rate)

        breakdown.append(
            CostComponent(name=component_name, tokens=tokens, cost_usd=cost_usd)
        )

    total_cost_usd = sum((c.cost_usd for c in breakdown), start=Decimal(0))

    logger.info(
        "cost.calculation.completed",
        model_name=model_name,
        total_cost_usd=str(
            total_cost_usd  # Convert Decimal to string to avoid JSON serialization issues
        ),
        component_count=len(breakdown),
    )

    return CostSuccess(
        model_name=model_name,
        breakdown=tuple(breakdown),
        total_cost_usd=total_cost_usd,
    )


def safe_calculate_cost(
    model_name: str,
    usage: LLMTokenUsage,
    *,
    pricing_config: PricingConfig | None = None,
) -> CostResult:
    try:
        return calculate_cost(model_name, usage, pricing_config=pricing_config)

    except CostError as exc:
        logger.warning(
            "cost.error.handled",
            model_name=model_name,
            error_type=exc.error_type,
            error_message=str(exc),
            exc_info=True,
        )

        return CostFailure(
            model_name=model_name,
            error_type=exc.error_type,
            error_message=str(exc),
        )
    except Exception as exc:
        # Intentionally broad - cost calculation must never crash the calling process
        logger.exception(
            "cost.error.unexpected",
            model_name=model_name,
        )

        return CostFailure(
            model_name=model_name,
            error_type="calculation_error",  # Any unexpected errors are given a generic type
            error_message=str(exc),
        )

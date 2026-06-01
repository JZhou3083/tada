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


def unsafe_calculate_cost(
    model_name: str,
    token_usage: LLMTokenUsage,
    *,
    pricing_config: PricingConfig | None = None,
) -> CostSuccess:
    """
    Estimate the USD cost of an LLM call from token usage.

    Args:
        model_name: Provider-reported model name.
        token_usage: Token usage for the request.
        pricing_config: Optional pricing configuration to override the library default.

    Returns:
        A `CostSuccess` containing the model name, a breakdown of costs by component,
        and the total estimated cost in USD.
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
        tokens = token_counter(token_usage)
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
    """
    Estimate the USD cost of an LLM call from token usage.

    Unlike `unsafe_calculate_cost`, this function handles recoverable failure cases
    gracefully, such as missing pricing data, without raising runtime errors.

    Args:
        model_name: Provider-reported model name.
        usage: Token usage for the request.
        pricing_config: Optional pricing configuration to override the library default.

    Returns:
        A `CostResult`, which is either:
        - `CostSuccess`: Contains the model name, a breakdown of costs by component,
          and the total estimated cost in USD.
        - `CostFailure`: Contains details about why the cost calculation could not be completed.
    """
    try:
        return unsafe_calculate_cost(model_name, usage, pricing_config=pricing_config)

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

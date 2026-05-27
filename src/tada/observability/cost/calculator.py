from __future__ import annotations

from decimal import Decimal
from typing import Callable

from tada.observability.cost.errors import (
    CostError,
    InvalidUsageError,
    PricingNotFoundError,
    UsageMissingError,
)
from tada.observability.cost.pricing import get_model_pricing, load_pricing_config
from tada.observability.cost.schemas import ModelPricing, PricingConfig
from tada.observability.cost.types import (
    CostComponent,
    CostFailure,
    CostResult,
    CostSuccess,
    LLMTokenUsage,
)

TokenCounter = Callable[[LLMTokenUsage], int]
RateGetter = Callable[[ModelPricing], Decimal | None]

COST_COMPONENTS: tuple[tuple[str, TokenCounter, RateGetter], ...] = (
    (
        "cached_input",
        lambda usage: _get_token_count(usage, "cached_content_token_count"),
        lambda pricing: (
            pricing.cached_input_cost_per_1m or pricing.input_cost_per_1m
        ),  # if cached input cost is not provided, fall back to regular input cost
    ),
    (
        "input",
        lambda usage: max(
            _get_token_count(usage, "prompt_token_count")
            - _get_token_count(usage, "cached_content_token_count"),
            0,
        ),
        lambda pricing: pricing.input_cost_per_1m,
    ),
    (
        "thoughts",
        lambda usage: _get_token_count(usage, "thoughts_token_count"),
        lambda pricing: pricing.thoughts_cost_per_1m,
    ),
    (
        "output",
        lambda usage: _get_token_count(usage, "candidates_token_count"),
        lambda pricing: pricing.output_cost_per_1m,
    ),
)


def _get_token_count(usage: LLMTokenUsage, key: str) -> int:
    """Return a non-negative token count from a usage payload."""
    value = usage.get(key, 0)

    if value is None:
        return 0

    # Since bool is a subclass of int specifically catch edge-case value: bool
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidUsageError(f"{key} must be an int, got {type(value).__name__}")

    if value < 0:
        raise InvalidUsageError(f"{key} must be non-negative")

    return value


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

    Pricing is resolved by exact model name first, then by prefix match.

    Args:
        model_name: Model name reported by the provider.
        usage: Token usage metrics for the request.

    Expected usage keys:
        prompt_token_count: Total prompt/input tokens.
        cached_content_token_count: Prompt tokens served from cache.
        thoughts_token_count: Internal reasoning/thinking tokens, if reported.
        candidates_token_count: Output/completion tokens.

    Returns:
        A dictionary containing the model name, per-component cost breakdown,
        and total estimated cost in USD.

    Notes:
        - Costs are returned as floats rounded to 6 decimal places.
        - Missing usage values are treated as zero.
        - Input cost excludes cached input tokens.
    """
    if usage is None:
        raise UsageMissingError("Usage data is missing or empty")

    if not pricing_config:
        pricing_config = load_pricing_config()

    model_pricing = get_model_pricing(model_name, pricing_config.pricing)

    if model_pricing is None:
        raise PricingNotFoundError(model_name)

    # Guard against invalid token usage figures - cached input cannot exceed full input
    prompt_tokens = _get_token_count(usage, "prompt_token_count")
    cached_tokens = _get_token_count(usage, "cached_content_token_count")

    if cached_tokens > prompt_tokens:
        raise InvalidUsageError(
            "cached_content_token_count cannot exceed prompt_token_count"
        )

    breakdown: list[CostComponent] = []
    for component_name, token_counter, rate_getter in COST_COMPONENTS:
        tokens = token_counter(usage)
        rate = rate_getter(model_pricing)
        cost_usd = _calculate_component_cost(tokens, rate)

        breakdown.append(
            CostComponent(name=component_name, tokens=tokens, cost_usd=cost_usd)
        )

    return CostSuccess(
        ok=True,
        model_name=model_name,
        breakdown=breakdown,
        total_cost_usd=sum(
            [component.cost_usd for component in breakdown], start=Decimal(0)
        ),
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
        return CostFailure(
            ok=False,
            model_name=model_name,
            breakdown=tuple(),
            total_cost_usd=None,
            error_type=exc.error_type,
            error_message=str(exc),
        )
    except Exception as exc:
        return CostFailure(
            ok=False,
            model_name=model_name,
            breakdown=tuple(),
            total_cost_usd=None,
            error_type="calculation_error",  # Any unexpected errors are given a generic type
            error_message=str(exc),
        )

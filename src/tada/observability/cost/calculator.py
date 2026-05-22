from __future__ import annotations

from decimal import Decimal
from typing import Callable

from tada.observability.cost.pricing import get_model_pricing, load_pricing_config
from tada.observability.cost.schemas import ModelPricing
from tada.observability.cost.types import CostComponent, CostResult, Usage

TokenCounter = Callable[[Usage], int]
RateGetter = Callable[[ModelPricing], Decimal | None]

COST_COMPONENTS: tuple[tuple[str, TokenCounter, RateGetter], ...] = (
    (
        "cached_input",
        lambda usage: get_token_count(usage, "cached_content_token_count"),
        lambda pricing: (
            pricing.cached_input_cost_per_1m or pricing.input_cost_per_1m
        ),  # if cached input cost is not provided, fall back to regular input cost
    ),
    (
        "input",
        lambda usage: max(
            get_token_count(usage, "prompt_token_count")
            - get_token_count(usage, "cached_content_token_count"),
            0,
        ),
        lambda pricing: pricing.input_cost_per_1m,
    ),
    (
        "thoughts",
        lambda usage: get_token_count(usage, "thoughts_token_count"),
        lambda pricing: pricing.thoughts_cost_per_1m,
    ),
    (
        "output",
        lambda usage: get_token_count(usage, "candidates_token_count"),
        lambda pricing: pricing.output_cost_per_1m,
    ),
)


def get_token_count(usage: Usage, key: str) -> int:
    """Return a non-negative token count from a usage payload."""
    value = usage.get(key, 0)

    if value is None:
        return 0

    # Since bool is a subclass of int specifically catch edge-case value: bool
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{key} must be an int, got {type(value).__name__}")

    if value < 0:
        raise ValueError(f"{key} must be non-negative")

    return value


def calculate_component_cost(
    tokens: int,
    rate_per_1m: Decimal | None,
) -> Decimal:
    """Calculate the USD cost for a token component using a per-1M token rate."""
    if not tokens or rate_per_1m is None:
        return Decimal("0")

    return Decimal(tokens) * rate_per_1m / Decimal("1000000")


def calculate_cost(model_name: str, usage: Usage) -> CostResult:
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

        If no pricing is found, the dictionary includes an error message and
        a zero total cost.

    Notes:
        - Costs are returned as floats rounded to 6 decimal places.
        - Missing usage values are treated as zero.
        - Input cost excludes cached input tokens.
        - Components with missing pricing rates are costed as zero.
    """
    pricing_config = load_pricing_config()
    model_pricing = get_model_pricing(model_name, pricing_config.pricing)

    if model_pricing is None:
        return {
            "model": model_name,
            "error": f"No pricing for {model_name}",
            "total_cost_usd": 0.0,
        }

    # Guard against invalid token usage figures - cached input cannot exceed full input
    prompt_tokens = get_token_count(usage, "prompt_token_count")
    cached_tokens = get_token_count(usage, "cached_content_token_count")

    if cached_tokens > prompt_tokens:
        raise ValueError("cached_content_token_count cannot exceed prompt_token_count")

    breakdown: dict[str, CostComponent] = {}
    total_cost = Decimal("0")

    for component_name, token_counter, rate_getter in COST_COMPONENTS:
        tokens = token_counter(usage)
        rate = rate_getter(model_pricing)
        cost = calculate_component_cost(tokens, rate)

        breakdown[component_name] = {
            "tokens": tokens,
            "cost": float(round(cost, 6)),
        }

        total_cost += cost

    return {
        "model": model_name,
        "breakdown": breakdown,
        "total_cost_usd": float(round(total_cost, 6)),
    }

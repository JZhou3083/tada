from __future__ import annotations

from functools import lru_cache
from importlib import resources
from typing import Any, Callable

import yaml

PRICING_PACKAGE = "tada.observability"
PRICING_FILE = "pricing.yaml"

Usage = dict[str, Any]
Pricing = dict[str, dict[str, float]]
TokenCounter = Callable[[Usage], int]


COST_COMPONENTS: tuple[tuple[str, str, TokenCounter], ...] = (
    (
        "cached_input",
        "cached_input_cost_per_1m",
        lambda usage: usage.get("cached_content_token_count") or 0,
    ),
    (
        "input",
        "input_cost_per_1m",
        lambda usage: max(
            (usage.get("prompt_token_count") or 0)
            - (usage.get("cached_content_token_count") or 0),
            0,
        ),
    ),
    (
        "thoughts",
        "thoughts_cost_per_1m",
        lambda usage: usage.get("thoughts_token_count") or 0,
    ),
    (
        "output",
        "output_cost_per_1m",
        lambda usage: usage.get("candidates_token_count") or 0,
    ),
)


@lru_cache(maxsize=1)
def load_pricing() -> Pricing:
    pricing_path = resources.files(PRICING_PACKAGE).joinpath(PRICING_FILE)
    raw_yaml = pricing_path.read_text(encoding="utf-8")

    data = yaml.safe_load(raw_yaml) or {}

    return data.get("pricing", {})


def get_model_pricing(model_name: str, pricing: Pricing) -> dict[str, float] | None:
    if model_name in pricing:
        return pricing[model_name]

    return next(
        (
            model_pricing
            for pricing_model, model_pricing in pricing.items()
            if model_name.startswith(pricing_model)
        ),
        None,
    )


def calculate_component_cost(tokens: int, rate_per_1m: float | None) -> float:
    if not tokens or not rate_per_1m:
        return 0.0

    return tokens * rate_per_1m / 1_000_000


def calculate_cost(model_name: str, usage: Usage) -> dict[str, Any]:
    pricing = load_pricing()
    model_pricing = get_model_pricing(model_name, pricing)

    if model_pricing is None:
        return {
            "model": model_name,
            "error": f"No pricing for {model_name}",
            "total_cost_usd": 0.0,
        }

    breakdown: dict[str, dict[str, float | int]] = {}
    total_cost = 0.0

    for component_name, rate_key, token_counter in COST_COMPONENTS:
        tokens = token_counter(usage)
        rate = model_pricing.get(rate_key)
        cost = calculate_component_cost(tokens, rate)

        breakdown[component_name] = {
            "tokens": tokens,
            "cost": round(cost, 6),
        }

        total_cost += cost

    return {
        "model": model_name,
        "breakdown": breakdown,
        "total_cost_usd": round(total_cost, 6),
    }

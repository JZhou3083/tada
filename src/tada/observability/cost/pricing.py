from __future__ import annotations

from functools import lru_cache
from importlib import resources

import yaml

from tada.observability.cost.schemas import ModelPricing, PricingConfig

Pricing = dict[str, ModelPricing]


@lru_cache(maxsize=1)
def load_pricing_config() -> PricingConfig:
    """Load, validate, and cache the packaged pricing YAML configuration."""
    pricing_path = resources.files("tada.observability.cost").joinpath("pricing.yaml")
    raw_yaml = pricing_path.read_text(encoding="utf-8")

    data = yaml.safe_load(raw_yaml) or {}

    return PricingConfig.model_validate(data)


def get_model_pricing(
    model_name: str,
    pricing: Pricing,
) -> ModelPricing | None:
    """Resolve pricing using exact match, then longest prefix match."""
    if model_name in pricing:
        return pricing[model_name]

    matches = [
        (pricing_model, model_pricing)
        for pricing_model, model_pricing in pricing.items()
        if model_name.startswith(pricing_model)
    ]

    if not matches:
        return None

    return max(matches, key=lambda item: len(item[0]))[1]

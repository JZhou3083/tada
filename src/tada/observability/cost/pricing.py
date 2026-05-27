from __future__ import annotations

from functools import lru_cache
from importlib import resources

import structlog
import yaml

from tada.observability.cost.schemas import ModelPricing, PricingConfig

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

Pricing = dict[str, ModelPricing]


@lru_cache(maxsize=1)
def load_pricing_config() -> PricingConfig:
    """Load, validate, and cache the packaged pricing YAML configuration."""
    logger.debug("cost.pricing.config_loading")

    pricing_path = resources.files("tada.observability.cost").joinpath("pricing.yaml")
    raw_yaml = pricing_path.read_text(encoding="utf-8")

    config = PricingConfig.model_validate(yaml.safe_load(raw_yaml))

    logger.info(
        "cost.pricing.config_loaded",
        pricing_path=str(pricing_path),
        model_count=len(config.pricing),
        currency=config.currency,
        unit=config.unit,
    )

    return config


def clear_pricing_cache() -> None:
    load_pricing_config.cache_clear()


def get_model_pricing(
    model_name: str,
    pricing: Pricing,
) -> ModelPricing | None:
    """Resolve pricing using exact match, then longest prefix match."""
    if model_name in pricing:
        logger.debug(
            "cost.pricing.resolved",
            model_name=model_name,
            matched_model_name=model_name,
            match_type="exact",
        )
        return pricing[model_name]

    # TODO: can we improve the prefix mapping whilst keeping it simple?
    matching_keys = [
        (pricing_model, model_pricing)
        for pricing_model, model_pricing in pricing.items()
        if model_name.startswith(pricing_model)
    ]

    if matching_keys:
        matched_key = max(matching_keys, key=lambda item: len(item[0]))[0]

        logger.debug(
            "cost.pricing.resolved",
            model_name=model_name,
            matched_model_name=matched_key,
            match_type="prefix",
        )

        return pricing[matched_key]

    logger.warning(
        "cost.pricing.not_found",
        model_name=model_name,
        available_model_count=len(pricing),
    )

    return None

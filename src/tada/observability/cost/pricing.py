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

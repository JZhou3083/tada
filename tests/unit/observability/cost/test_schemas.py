from datetime import date
from decimal import Decimal

import pytest
from pydantic import HttpUrl, ValidationError

from tada.observability.cost.schemas import ModelPricing, PricingConfig


@pytest.mark.unit
def test_model_pricing_accepts_valid_pricing():
    pricing = ModelPricing(
        input_cost_per_1m=Decimal("1.00"),
        output_cost_per_1m=Decimal("2.00"),
        effective_from=date(2025, 1, 1),
        source=HttpUrl("https://example.com/pricing"),
    )

    assert pricing.input_cost_per_1m == Decimal("1.00")


@pytest.mark.unit
def test_model_pricing_rejects_negative_cost():
    with pytest.raises(ValidationError):
        ModelPricing(
            input_cost_per_1m=Decimal("-1.00"),
            output_cost_per_1m=Decimal("2.00"),
            effective_from=date(2025, 1, 1),
            source=HttpUrl("https://example.com/pricing"),
        )


@pytest.mark.unit
def test_pricing_config_rejects_empty_pricing():
    with pytest.raises(
        ValidationError, match="pricing must contain at least one model entry"
    ):
        PricingConfig(
            currency="USD",
            unit="tokens_per_million",
            pricing={},
        )


@pytest.mark.unit
def test_pricing_config_rejects_wrong_currency(model_pricing):
    with pytest.raises(ValidationError):
        PricingConfig(
            currency="GBP",  # type: ignore[arg-type]
            unit="tokens_per_million",
            pricing={"model": model_pricing},
        )

from datetime import date
from decimal import Decimal

import pytest
from pydantic import HttpUrl

from tada.observability.cost.schemas import ModelPricing


@pytest.fixture
def model_pricing() -> ModelPricing:
    return ModelPricing(
        input_cost_per_1m=Decimal("1.25"),
        output_cost_per_1m=Decimal("10.00"),
        cached_input_cost_per_1m=Decimal("0.125"),
        thoughts_cost_per_1m=Decimal("10.00"),
        effective_from=date(2025, 1, 1),
        source=HttpUrl("https://example.com/pricing"),
    )


@pytest.fixture
def pricing(model_pricing: ModelPricing) -> dict[str, ModelPricing]:
    return {
        "gemini-2.5-flash": model_pricing,
        "gemini-2.5": model_pricing,
    }


@pytest.fixture
def usage() -> dict[str, int]:
    return {
        "prompt_token_count": 1_000,
        "cached_content_token_count": 200,
        "thoughts_token_count": 50,
        "candidates_token_count": 300,
    }

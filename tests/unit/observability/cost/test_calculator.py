from decimal import Decimal
from typing import Any, cast

import pytest

from tada.observability.cost.calculator import (
    calculate_component_cost,
    calculate_cost,
    get_token_count,
)
from tada.observability.cost.schemas import PricingConfig
from tada.observability.cost.types import Usage


@pytest.mark.unit
def test_get_token_count_returns_value():
    usage: Usage = {"prompt_token_count": 123}

    assert get_token_count(usage, "prompt_token_count") == 123


@pytest.mark.unit
def test_get_token_count_defaults_missing_value_to_zero():
    usage: Usage = {}

    assert get_token_count(usage, "prompt_token_count") == 0


@pytest.mark.unit
def test_get_token_count_treats_none_as_zero():
    usage: Usage = {"prompt_token_count": None}

    assert get_token_count(usage, "prompt_token_count") == 0


@pytest.mark.unit
def test_get_token_count_rejects_non_int_value():
    usage = cast(Any, {"prompt_token_count": "123"})

    with pytest.raises(TypeError, match="prompt_token_count must be an int"):
        get_token_count(usage, "prompt_token_count")


@pytest.mark.unit
def test_get_token_count_rejects_negative_value():
    with pytest.raises(ValueError, match="prompt_token_count must be non-negative"):
        get_token_count({"prompt_token_count": -1}, "prompt_token_count")


@pytest.mark.unit
def test_calculate_component_cost():
    assert calculate_component_cost(1_000_000, Decimal("1.25")) == Decimal("1.25")


@pytest.mark.unit
def test_calculate_component_cost_returns_zero_for_missing_rate():
    assert calculate_component_cost(1_000, None) == Decimal("0")


@pytest.mark.unit
def test_calculate_component_cost_returns_zero_for_zero_tokens():
    assert calculate_component_cost(0, Decimal("1.25")) == Decimal("0")


@pytest.mark.unit
def test_calculate_cost_breaks_down_components(monkeypatch, model_pricing, usage):
    pricing_config = PricingConfig(
        currency="USD",
        unit="tokens_per_million",
        pricing={"gemini-2.5-flash": model_pricing},
    )

    monkeypatch.setattr(
        "tada.observability.cost.calculator.load_pricing_config",
        lambda: pricing_config,
    )

    result = calculate_cost("gemini-2.5-flash", usage)

    assert "error" not in result
    assert result["model"] == "gemini-2.5-flash"
    assert result["breakdown"]["cached_input"]["tokens"] == 200
    assert result["breakdown"]["input"]["tokens"] == 800
    assert result["breakdown"]["thoughts"]["tokens"] == 50
    assert result["breakdown"]["output"]["tokens"] == 300
    assert result["total_cost_usd"] > 0


@pytest.mark.unit
def test_calculate_cost_returns_error_for_unknown_model(monkeypatch, model_pricing):
    pricing_config = PricingConfig(
        currency="USD",
        unit="tokens_per_million",
        pricing={"known-model": model_pricing},
    )

    monkeypatch.setattr(
        "tada.observability.cost.calculator.load_pricing_config",
        lambda: pricing_config,
    )

    result = calculate_cost("unknown-model", {})

    assert result == {
        "model": "unknown-model",
        "error": "No pricing for unknown-model",
        "total_cost_usd": 0.0,
    }


@pytest.mark.unit
def test_calculate_cost_rejects_cached_tokens_greater_than_prompt_tokens(
    monkeypatch,
    model_pricing,
):
    pricing_config = PricingConfig(
        currency="USD",
        unit="tokens_per_million",
        pricing={"gemini-2.5-flash": model_pricing},
    )

    monkeypatch.setattr(
        "tada.observability.cost.calculator.load_pricing_config",
        lambda: pricing_config,
    )

    usage: Usage = {
        "prompt_token_count": 100,
        "cached_content_token_count": 200,
    }

    with pytest.raises(
        ValueError,
        match="cached_content_token_count cannot exceed prompt_token_count",
    ):
        calculate_cost("gemini-2.5-flash", usage)

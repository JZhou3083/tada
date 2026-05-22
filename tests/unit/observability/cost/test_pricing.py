import pytest

from tada.observability.cost.pricing import get_model_pricing


@pytest.mark.unit
def test_get_model_pricing_uses_exact_match(pricing):
    result = get_model_pricing("gemini-2.5-flash", pricing)

    assert result is pricing["gemini-2.5-flash"]


@pytest.mark.unit
def test_get_model_pricing_uses_longest_prefix_match(pricing):
    result = get_model_pricing("gemini-2.5-flash-001", pricing)

    assert result is pricing["gemini-2.5-flash"]


@pytest.mark.unit
def test_get_model_pricing_returns_none_when_no_match(pricing):
    result = get_model_pricing("unknown-model", pricing)

    assert result is None

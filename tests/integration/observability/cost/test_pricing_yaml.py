import pytest

from tada.observability.cost.pricing import load_pricing_config


@pytest.mark.integration
def test_packaged_pricing_yaml_loads():
    config = load_pricing_config()

    assert config.currency == "USD"
    assert config.unit == "tokens_per_million"
    assert config.pricing

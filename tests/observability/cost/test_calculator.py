"""Tests for the cost calculation module."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from pydantic import HttpUrl

from tada.observability.cost import calculate_cost, safe_calculate_cost
from tada.observability.cost.calculator import _get_token_count
from tada.observability.cost.errors import InvalidUsageError, PricingNotFoundError
from tada.observability.cost.pricing import clear_pricing_cache
from tada.observability.cost.schemas import ModelPricing, PricingConfig
from tada.observability.cost.types import CostFailure, CostSuccess

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_pricing_cache():
    """Isolate tests from each other by clearing the LRU cache after each test."""
    yield
    clear_pricing_cache()


@pytest.fixture
def model_pricing_full() -> ModelPricing:
    """ModelPricing with all optional fields set, giving known rates for assertions."""
    return ModelPricing(
        input_cost_per_1m=Decimal("1.00"),
        output_cost_per_1m=Decimal("2.00"),
        cached_input_cost_per_1m=Decimal("0.50"),
        thoughts_cost_per_1m=Decimal("1.50"),
        effective_from=date(2024, 1, 1),
        source=HttpUrl("https://example.com/pricing"),
    )


@pytest.fixture
def model_pricing_minimal() -> ModelPricing:
    """ModelPricing with only required fields — no cached or thoughts rates."""
    return ModelPricing(
        input_cost_per_1m=Decimal("1.00"),
        output_cost_per_1m=Decimal("2.00"),
        effective_from=date(2024, 1, 1),
        source=HttpUrl("https://example.com/pricing"),
    )


@pytest.fixture
def pricing_config(model_pricing_full, model_pricing_minimal) -> PricingConfig:
    return PricingConfig(
        currency="USD",
        unit="tokens_per_million",
        pricing={
            "test-model-full": model_pricing_full,
            "test-model-minimal": model_pricing_minimal,
        },
    )


# ---------------------------------------------------------------------------
# _get_token_count
# ---------------------------------------------------------------------------


class TestGetTokenCount:
    def test_returns_value_for_present_key(self):
        assert (
            _get_token_count({"prompt_token_count": 100}, "prompt_token_count") == 100
        )

    def test_returns_zero_for_missing_key(self):
        assert _get_token_count({}, "prompt_token_count") == 0

    def test_returns_zero_for_none_value(self):
        assert _get_token_count({"prompt_token_count": None}, "prompt_token_count") == 0

    def test_accepts_zero(self):
        assert _get_token_count({"prompt_token_count": 0}, "prompt_token_count") == 0

    @pytest.mark.parametrize("bad_value", [True, False])
    def test_raises_for_bool(self, bad_value):
        # bool is a subclass of int and must be explicitly rejected
        with pytest.raises(InvalidUsageError, match="must be an int, got bool"):
            _get_token_count({"prompt_token_count": bad_value}, "prompt_token_count")

    @pytest.mark.parametrize("bad_value", [1.5, "100", [100]])
    def test_raises_for_non_int(self, bad_value):
        with pytest.raises(InvalidUsageError, match="must be an int"):
            _get_token_count({"prompt_token_count": bad_value}, "prompt_token_count")

    def test_raises_for_negative(self):
        with pytest.raises(InvalidUsageError, match="must be non-negative"):
            _get_token_count({"prompt_token_count": -1}, "prompt_token_count")

    def test_error_message_includes_key_name(self):
        """Ensures the error message is useful regardless of which key fails."""
        with pytest.raises(InvalidUsageError, match="candidates_token_count"):
            _get_token_count({"candidates_token_count": -5}, "candidates_token_count")


# ---------------------------------------------------------------------------
# calculate_cost — return type and structure
# ---------------------------------------------------------------------------


class TestCalculateCostReturnType:
    def test_returns_cost_success_instance(self, pricing_config):
        result = calculate_cost("test-model-full", {}, pricing_config=pricing_config)
        assert isinstance(result, CostSuccess)

    def test_ok_is_true(self, pricing_config):
        result = calculate_cost("test-model-full", {}, pricing_config=pricing_config)
        assert result.ok is True

    def test_model_name_preserved(self, pricing_config):
        result = calculate_cost("test-model-full", {}, pricing_config=pricing_config)
        assert result.model_name == "test-model-full"

    def test_breakdown_is_tuple(self, pricing_config):
        result = calculate_cost("test-model-full", {}, pricing_config=pricing_config)
        assert isinstance(result.breakdown, tuple)

    def test_breakdown_has_four_components(self, pricing_config):
        result = calculate_cost("test-model-full", {}, pricing_config=pricing_config)
        assert len(result.breakdown) == 4

    def test_breakdown_component_names_and_order(self, pricing_config):
        result = calculate_cost("test-model-full", {}, pricing_config=pricing_config)
        assert [c.name for c in result.breakdown] == [
            "cached_input",
            "input",
            "thoughts",
            "output",
        ]

    def test_total_equals_sum_of_breakdown(self, pricing_config):
        result = calculate_cost(
            "test-model-full",
            {
                "prompt_token_count": 1_000_000,
                "cached_content_token_count": 200_000,
                "thoughts_token_count": 100_000,
                "candidates_token_count": 500_000,
            },
            pricing_config=pricing_config,
        )
        assert result.total_cost_usd == sum(c.cost_usd for c in result.breakdown)

    def test_total_cost_is_decimal(self, pricing_config):
        result = calculate_cost(
            "test-model-full",
            {"candidates_token_count": 1_000_000},
            pricing_config=pricing_config,
        )
        assert isinstance(result.total_cost_usd, Decimal)


# ---------------------------------------------------------------------------
# calculate_cost — cost arithmetic
# ---------------------------------------------------------------------------


class TestCalculateCostArithmetic:
    def test_empty_usage_produces_zero_cost(self, pricing_config):
        result = calculate_cost("test-model-full", {}, pricing_config=pricing_config)
        assert result.total_cost_usd == Decimal("0")

    def test_output_cost(self, pricing_config):
        # output_cost_per_1m = 2.00 → 1M tokens = $2.00
        result = calculate_cost(
            "test-model-full",
            {"candidates_token_count": 1_000_000},
            pricing_config=pricing_config,
        )
        output = next(c for c in result.breakdown if c.name == "output")
        assert output.cost_usd == Decimal("2.00")

    def test_input_cost_excludes_cached_tokens(self, pricing_config):
        # 1M prompt, 400k cached → 600k non-cached input tokens
        # input_cost_per_1m = 1.00 → 600k tokens = $0.60
        result = calculate_cost(
            "test-model-full",
            {
                "prompt_token_count": 1_000_000,
                "cached_content_token_count": 400_000,
            },
            pricing_config=pricing_config,
        )
        input_component = next(c for c in result.breakdown if c.name == "input")
        assert input_component.tokens == 600_000
        assert input_component.cost_usd == Decimal("0.60")

    def test_cached_input_uses_dedicated_rate_when_set(self, pricing_config):
        # cached_input_cost_per_1m = 0.50 → 1M tokens = $0.50
        result = calculate_cost(
            "test-model-full",
            {
                "prompt_token_count": 1_000_000,
                "cached_content_token_count": 1_000_000,
            },
            pricing_config=pricing_config,
        )
        cached = next(c for c in result.breakdown if c.name == "cached_input")
        assert cached.cost_usd == Decimal("0.50")

    def test_cached_input_falls_back_to_input_rate(self, pricing_config):
        # test-model-minimal has no cached_input_cost_per_1m
        # so cached tokens billed at input_cost_per_1m = 1.00
        result = calculate_cost(
            "test-model-minimal",
            {
                "prompt_token_count": 1_000_000,
                "cached_content_token_count": 1_000_000,
            },
            pricing_config=pricing_config,
        )
        cached = next(c for c in result.breakdown if c.name == "cached_input")
        assert cached.cost_usd == Decimal("1.00")

    def test_thoughts_cost(self, pricing_config):
        # thoughts_cost_per_1m = 1.50 → 1M tokens = $1.50
        result = calculate_cost(
            "test-model-full",
            {"thoughts_token_count": 1_000_000},
            pricing_config=pricing_config,
        )
        thoughts = next(c for c in result.breakdown if c.name == "thoughts")
        assert thoughts.cost_usd == Decimal("1.50")

    def test_thoughts_cost_is_zero_when_rate_not_configured(self, pricing_config):
        result = calculate_cost(
            "test-model-minimal",
            {"thoughts_token_count": 1_000_000},
            pricing_config=pricing_config,
        )
        thoughts = next(c for c in result.breakdown if c.name == "thoughts")
        assert thoughts.cost_usd == Decimal("0")

    def test_input_tokens_cannot_go_negative_when_cached_equals_prompt(
        self, pricing_config
    ):
        # All prompt tokens are cached — non-cached input should be exactly 0
        result = calculate_cost(
            "test-model-full",
            {
                "prompt_token_count": 500_000,
                "cached_content_token_count": 500_000,
            },
            pricing_config=pricing_config,
        )
        input_component = next(c for c in result.breakdown if c.name == "input")
        assert input_component.tokens == 0
        assert input_component.cost_usd == Decimal("0")


# ---------------------------------------------------------------------------
# calculate_cost — error cases
# ---------------------------------------------------------------------------


class TestCalculateCostErrors:
    def test_raises_pricing_not_found_for_unknown_model(self, pricing_config):
        with pytest.raises(PricingNotFoundError, match="unknown-model"):
            calculate_cost("unknown-model", {}, pricing_config=pricing_config)

    def test_raises_invalid_usage_when_cached_exceeds_prompt(self, pricing_config):
        with pytest.raises(
            InvalidUsageError,
            match="cached_content_token_count cannot exceed prompt_token_count",
        ):
            calculate_cost(
                "test-model-full",
                {"prompt_token_count": 100, "cached_content_token_count": 200},
                pricing_config=pricing_config,
            )

    def test_raises_invalid_usage_for_bad_token_type(self, pricing_config):
        with pytest.raises(InvalidUsageError):
            calculate_cost(
                "test-model-full",
                {"prompt_token_count": "not-an-int"},  # type: ignore[typeddict-item]
                pricing_config=pricing_config,
            )

    def test_uses_injected_pricing_config_not_disk(self, pricing_config):
        """Passing pricing_config should bypass disk loading entirely."""
        with patch(
            "tada.observability.cost.calculator.load_pricing_config",
            side_effect=AssertionError("should not load from disk"),
        ):
            result = calculate_cost(
                "test-model-full", {}, pricing_config=pricing_config
            )
        assert isinstance(result, CostSuccess)


# ---------------------------------------------------------------------------
# safe_calculate_cost
# ---------------------------------------------------------------------------


class TestSafeCalculateCost:
    def test_returns_cost_success_on_valid_input(self, pricing_config):
        result = safe_calculate_cost(
            "test-model-full",
            {"prompt_token_count": 1000, "candidates_token_count": 500},
            pricing_config=pricing_config,
        )
        assert isinstance(result, CostSuccess)

    def test_returns_cost_failure_for_unknown_model(self, pricing_config):
        result = safe_calculate_cost("unknown-model", {}, pricing_config=pricing_config)
        assert isinstance(result, CostFailure)
        assert result.ok is False
        assert result.error_type == "pricing_not_found"

    def test_returns_cost_failure_for_invalid_usage(self, pricing_config):
        result = safe_calculate_cost(
            "test-model-full",
            {"prompt_token_count": 100, "cached_content_token_count": 200},
            pricing_config=pricing_config,
        )
        assert isinstance(result, CostFailure)
        assert result.error_type == "invalid_usage"

    def test_returns_cost_failure_for_unexpected_exception(self, pricing_config):
        with patch(
            "tada.observability.cost.calculator.load_pricing_config",
            side_effect=RuntimeError("unexpected failure"),
        ):
            result = safe_calculate_cost("test-model-full", {})

        assert isinstance(result, CostFailure)
        assert result.error_type == "calculation_error"
        assert "unexpected failure" in result.error_message

    def test_never_raises_on_any_exception(self, pricing_config):
        """The broad except clause must hold even for non-CostError exceptions."""
        with patch(
            "tada.observability.cost.calculator._calculate_component_cost",
            side_effect=MemoryError("oom"),
        ):
            result = safe_calculate_cost(
                "test-model-full", {}, pricing_config=pricing_config
            )
        assert isinstance(result, CostFailure)

    def test_failure_preserves_model_name(self, pricing_config):
        result = safe_calculate_cost("unknown-model", {}, pricing_config=pricing_config)
        assert result.model_name == "unknown-model"

    def test_failure_error_message_is_informative(self, pricing_config):
        result = safe_calculate_cost("unknown-model", {}, pricing_config=pricing_config)
        assert isinstance(result, CostFailure)
        assert "unknown-model" in result.error_message

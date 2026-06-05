"""Tests for the cost calculation module."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from pydantic import HttpUrl, ValidationError

from tada.observability.cost import (
    CostFailure,
    CostSuccess,
    ModelPricing,
    PricingConfig,
    PricingNotFoundError,
    load_pricing_config,
    safe_calculate_cost,
    unsafe_calculate_cost,
)
from tada.observability.cost.types import LLMTokenUsage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_pricing_cache():
    """Isolate tests from each other by clearing the LRU cache after each test."""
    yield
    load_pricing_config.cache_clear()


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
        unit="per_1m_tokens",
        pricing={
            "test-model-full": model_pricing_full,
            "test-model-minimal": model_pricing_minimal,
        },
    )


@pytest.fixture
def minimal_usage() -> LLMTokenUsage:
    return LLMTokenUsage(input_tokens=0, output_tokens=0)


# ---------------------------------------------------------------------------
# unsafe_calculate_cost — return type and structure
# ---------------------------------------------------------------------------


class TestUnsafeCalculateCostReturnType:
    def test_returns_cost_success_instance(self, pricing_config, minimal_usage):
        result = unsafe_calculate_cost(
            "test-model-full",
            minimal_usage,
            pricing_config=pricing_config,
        )

        assert isinstance(result, CostSuccess)

    def test_model_name_preserved(self, pricing_config, minimal_usage):
        result = unsafe_calculate_cost(
            "test-model-full",
            minimal_usage,
            pricing_config=pricing_config,
        )

        assert result.model_name == "test-model-full"

    def test_breakdown_is_tuple(self, pricing_config, minimal_usage):
        result = unsafe_calculate_cost(
            "test-model-full",
            minimal_usage,
            pricing_config=pricing_config,
        )

        assert isinstance(result.breakdown, tuple)

    def test_breakdown_has_four_components(self, pricing_config, minimal_usage):
        result = unsafe_calculate_cost(
            "test-model-full",
            minimal_usage,
            pricing_config=pricing_config,
        )

        assert len(result.breakdown) == 4

    def test_breakdown_component_names_and_order(self, pricing_config, minimal_usage):
        result = unsafe_calculate_cost(
            "test-model-full",
            minimal_usage,
            pricing_config=pricing_config,
        )

        assert [c.name for c in result.breakdown] == [
            "cached_input",
            "input",
            "thoughts",
            "output",
        ]

    def test_total_equals_sum_of_breakdown(self, pricing_config):
        usage = LLMTokenUsage(
            input_tokens=1_000_000,
            cached_input_tokens=200_000,
            thoughts_tokens=100_000,
            output_tokens=500_000,
        )

        result = unsafe_calculate_cost(
            "test-model-full",
            usage,
            pricing_config=pricing_config,
        )

        assert result.total_cost_usd == sum(c.cost_usd for c in result.breakdown)

    def test_total_cost_is_decimal(self, pricing_config):
        usage = LLMTokenUsage(output_tokens=1_000_000)

        result = unsafe_calculate_cost(
            "test-model-full",
            usage,
            pricing_config=pricing_config,
        )

        assert isinstance(result.total_cost_usd, Decimal)


# ---------------------------------------------------------------------------
# unsafe_calculate_cost — cost arithmetic
# ---------------------------------------------------------------------------


class TestUnsafeCalculateCostArithmetic:
    def test_zero_tokens_produces_zero_cost(self, pricing_config, minimal_usage):
        result = unsafe_calculate_cost(
            "test-model-full",
            minimal_usage,
            pricing_config=pricing_config,
        )

        assert result.total_cost_usd == Decimal("0")

    def test_output_cost(self, pricing_config):
        # output_cost_per_1m = 2.00 → 1M tokens = $2.00
        usage = LLMTokenUsage(output_tokens=1_000_000)

        result = unsafe_calculate_cost(
            "test-model-full",
            usage,
            pricing_config=pricing_config,
        )

        output = next(c for c in result.breakdown if c.name == "output")
        assert output.tokens == 1_000_000
        assert output.cost_usd == Decimal("2.00")

    def test_input_cost_excludes_cached_tokens(self, pricing_config):
        # 1M input, 400k cached → 600k non-cached input tokens
        # input_cost_per_1m = 1.00 → 600k tokens = $0.60
        usage = LLMTokenUsage(
            input_tokens=1_000_000,
            cached_input_tokens=400_000,
        )

        result = unsafe_calculate_cost(
            "test-model-full",
            usage,
            pricing_config=pricing_config,
        )

        input_component = next(c for c in result.breakdown if c.name == "input")
        assert input_component.tokens == 600_000
        assert input_component.cost_usd == Decimal("0.60")

    def test_cached_input_uses_dedicated_rate_when_set(self, pricing_config):
        # cached_input_cost_per_1m = 0.50 → 1M tokens = $0.50
        usage = LLMTokenUsage(
            input_tokens=1_000_000,
            cached_input_tokens=1_000_000,
        )

        result = unsafe_calculate_cost(
            "test-model-full",
            usage,
            pricing_config=pricing_config,
        )

        cached = next(c for c in result.breakdown if c.name == "cached_input")
        assert cached.tokens == 1_000_000
        assert cached.cost_usd == Decimal("0.50")

    def test_cached_input_falls_back_to_input_rate(self, pricing_config):
        # test-model-minimal has no cached_input_cost_per_1m
        # so cached tokens are billed at input_cost_per_1m = 1.00
        usage = LLMTokenUsage(
            input_tokens=1_000_000,
            cached_input_tokens=1_000_000,
        )

        result = unsafe_calculate_cost(
            "test-model-minimal",
            usage,
            pricing_config=pricing_config,
        )

        cached = next(c for c in result.breakdown if c.name == "cached_input")
        assert cached.tokens == 1_000_000
        assert cached.cost_usd == Decimal("1.00")

    def test_thoughts_cost(self, pricing_config):
        # thoughts_cost_per_1m = 1.50 → 1M tokens = $1.50
        usage = LLMTokenUsage(
            input_tokens=0,
            thoughts_tokens=1_000_000,
        )

        result = unsafe_calculate_cost(
            "test-model-full",
            usage,
            pricing_config=pricing_config,
        )

        thoughts = next(c for c in result.breakdown if c.name == "thoughts")
        assert thoughts.tokens == 1_000_000
        assert thoughts.cost_usd == Decimal("1.50")

    def test_thoughts_cost_is_zero_when_rate_not_configured(self, pricing_config):
        usage = LLMTokenUsage(
            input_tokens=0,
            thoughts_tokens=1_000_000,
        )

        result = unsafe_calculate_cost(
            "test-model-minimal",
            usage,
            pricing_config=pricing_config,
        )

        thoughts = next(c for c in result.breakdown if c.name == "thoughts")
        assert thoughts.tokens == 1_000_000
        assert thoughts.cost_usd == Decimal("0")

    def test_input_tokens_cannot_go_negative_when_cached_equals_input(
        self,
        pricing_config,
    ):
        # All input tokens are cached — non-cached input should be exactly 0
        usage = LLMTokenUsage(
            input_tokens=500_000,
            cached_input_tokens=500_000,
        )

        result = unsafe_calculate_cost(
            "test-model-full",
            usage,
            pricing_config=pricing_config,
        )

        input_component = next(c for c in result.breakdown if c.name == "input")
        assert input_component.tokens == 0
        assert input_component.cost_usd == Decimal("0")


# ---------------------------------------------------------------------------
# LLMTokenUsage — validation
# ---------------------------------------------------------------------------


class TestLLMTokenUsageValidation:
    def test_requires_input_or_output_tokens(self):
        with pytest.raises(
            ValidationError,
            match="Usage must include input_tokens or output_tokens",
        ):
            LLMTokenUsage()

    def test_cached_input_tokens_cannot_exceed_input_tokens(self):
        with pytest.raises(
            ValidationError,
            match="cached_input_tokens cannot exceed input_tokens",
        ):
            LLMTokenUsage(
                input_tokens=100,
                cached_input_tokens=200,
            )

    def test_rejects_bad_token_type(self):
        with pytest.raises(ValidationError):
            LLMTokenUsage(
                input_tokens="not-an-int",  # type: ignore[arg-type]
            )

    def test_rejects_negative_tokens(self):
        with pytest.raises(ValidationError):
            LLMTokenUsage(
                input_tokens=-1,
            )


# ---------------------------------------------------------------------------
# unsafe_calculate_cost — error cases
# ---------------------------------------------------------------------------


class TestUnsafeCalculateCostErrors:
    def test_raises_pricing_not_found_for_unknown_model(
        self,
        pricing_config,
        minimal_usage,
    ):
        with pytest.raises(PricingNotFoundError, match="unknown-model"):
            unsafe_calculate_cost(
                "unknown-model",
                minimal_usage,
                pricing_config=pricing_config,
            )

    def test_uses_injected_pricing_config_not_disk(self, pricing_config, minimal_usage):
        """Passing pricing_config should bypass disk loading entirely."""
        with patch(
            "tada.observability.cost.calculator.load_pricing_config",
            side_effect=AssertionError("should not load from disk"),
        ):
            result = unsafe_calculate_cost(
                "test-model-full",
                minimal_usage,
                pricing_config=pricing_config,
            )

        assert isinstance(result, CostSuccess)


# ---------------------------------------------------------------------------
# safe_calculate_cost
# ---------------------------------------------------------------------------


class TestSafeCalculateCost:
    def test_returns_cost_success_on_valid_input(self, pricing_config):
        usage = LLMTokenUsage(
            input_tokens=1_000,
            output_tokens=500,
        )

        result = safe_calculate_cost(
            "test-model-full",
            usage,
            pricing_config=pricing_config,
        )

        assert isinstance(result, CostSuccess)

    def test_returns_cost_failure_for_unknown_model(
        self, pricing_config, minimal_usage
    ):
        result = safe_calculate_cost(
            "unknown-model",
            minimal_usage,
            pricing_config=pricing_config,
        )

        assert isinstance(result, CostFailure)
        assert result.error_type == "pricing_not_found"

    def test_returns_cost_failure_for_unexpected_exception(self):
        usage = LLMTokenUsage(input_tokens=1)

        with patch(
            "tada.observability.cost.calculator.load_pricing_config",
            side_effect=RuntimeError("unexpected failure"),
        ):
            result = safe_calculate_cost("test-model-full", usage)

        assert isinstance(result, CostFailure)
        assert result.error_type == "calculation_error"
        assert "unexpected failure" in result.error_message

    def test_never_raises_on_any_exception(self, pricing_config, minimal_usage):
        """The broad except clause must hold even for non-CostError exceptions."""
        with patch(
            "tada.observability.cost.calculator._calculate_component_cost",
            side_effect=MemoryError("oom"),
        ):
            result = safe_calculate_cost(
                "test-model-full",
                minimal_usage,
                pricing_config=pricing_config,
            )

        assert isinstance(result, CostFailure)
        assert result.error_type == "calculation_error"
        assert "oom" in result.error_message

    def test_failure_preserves_model_name(self, pricing_config, minimal_usage):
        result = safe_calculate_cost(
            "unknown-model",
            minimal_usage,
            pricing_config=pricing_config,
        )

        assert result.model_name == "unknown-model"

    def test_failure_error_message_is_informative(self, pricing_config, minimal_usage):
        result = safe_calculate_cost(
            "unknown-model",
            minimal_usage,
            pricing_config=pricing_config,
        )

        assert isinstance(result, CostFailure)
        assert "unknown-model" in result.error_message

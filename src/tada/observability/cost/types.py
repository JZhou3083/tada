from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LLMTokenUsage(BaseModel):
    """Token usage metrics returned by the model provider."""

    model_config = ConfigDict(extra="forbid")

    input_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    thoughts_tokens: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_usage_shape(self) -> Self:
        if self.input_tokens is None and self.output_tokens is None:
            raise ValueError("Usage must include input_tokens or output_tokens.")

        if (
            self.input_tokens is not None
            and self.cached_input_tokens is not None
            and self.cached_input_tokens > self.input_tokens
        ):
            raise ValueError("cached_input_tokens cannot exceed input_tokens.")

        return self

    @property
    def billable_input_tokens(self) -> int:
        return max(
            (self.input_tokens or 0) - (self.cached_input_tokens or 0),
            0,
        )

    @property
    def billable_cached_input_tokens(self) -> int:
        return self.cached_input_tokens or 0

    @property
    def billable_output_tokens(self) -> int:
        return self.output_tokens or 0

    @property
    def billable_thoughts_tokens(self) -> int:
        return self.thoughts_tokens or 0

    @property
    def total_tokens(self) -> int:
        return (
            self.billable_input_tokens
            + self.billable_thoughts_tokens
            + self.billable_output_tokens
        )


@dataclass(frozen=True)
class CostComponent(BaseModel):
    """Cost breakdown for a single token component."""

    name: str
    tokens: int
    cost_usd: Decimal


@dataclass(frozen=True)
class CostSuccess:
    """Successful cost calculation result."""

    model_name: str
    breakdown: tuple[CostComponent, ...]
    total_cost_usd: Decimal


@dataclass(frozen=True)
class CostFailure:
    """Cost calculation result when cost cannot be calculated."""

    model_name: str
    error_type: str
    error_message: str


type CostResult = CostSuccess | CostFailure

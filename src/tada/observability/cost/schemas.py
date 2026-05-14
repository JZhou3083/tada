from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
)

ModelName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class ModelPricing(BaseModel):
    """Pricing metadata and token rates for a single model."""

    model_config = ConfigDict(extra="forbid")

    input_cost_per_1m: Decimal = Field(ge=0)
    output_cost_per_1m: Decimal = Field(ge=0)
    cached_input_cost_per_1m: Decimal | None = Field(default=None, ge=0)
    thoughts_cost_per_1m: Decimal | None = Field(default=None, ge=0)

    max_prompt_tokens: int | None = Field(default=None, gt=0)
    cache_storage_cost_per_1m_tokens_per_hr: Decimal | None = Field(default=None, ge=0)

    effective_from: date
    source: HttpUrl


class PricingConfig(BaseModel):
    """Top-level schema for the pricing YAML file."""

    model_config = ConfigDict(extra="forbid")

    currency: Literal["USD"]
    unit: Literal["tokens_per_million"]
    pricing: dict[ModelName, ModelPricing]

    @field_validator("pricing")
    @classmethod
    def pricing_must_not_be_empty(
        cls,
        value: dict[ModelName, ModelPricing],
    ) -> dict[ModelName, ModelPricing]:
        """Ensure at least one model pricing entry exists."""
        if not value:
            raise ValueError("pricing must contain at least one model entry")
        return value

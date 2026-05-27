from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict


class LLMTokenUsage(TypedDict, total=False):
    """Token usage metrics returned by the model provider."""

    prompt_token_count: int | None
    cached_content_token_count: int | None
    thoughts_token_count: int | None
    candidates_token_count: int | None


@dataclass(frozen=True, slots=True)
class CostComponent:
    """Cost breakdown for a single token component."""

    name: str
    tokens: int
    cost_usd: Decimal


# TODO: remove OK discriminator and just use type checks?
@dataclass(frozen=True, slots=True)
class CostSuccess:
    """Successful cost calculation result."""

    model_name: str
    breakdown: tuple[CostComponent, ...]
    total_cost_usd: Decimal


@dataclass(frozen=True, slots=True)
class CostFailure:
    """Cost calculation result when cost cannot be calculated."""

    model_name: str
    error_type: str
    error_message: str


type CostResult = CostSuccess | CostFailure

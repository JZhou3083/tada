from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, TypedDict


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


@dataclass(frozen=True, slots=True)
class CostSuccess:
    """Successful cost calculation result."""

    ok: Literal[True]
    model_name: str
    breakdown: list[CostComponent]
    total_cost_usd: Decimal


@dataclass(frozen=True, slots=True)
class CostFailure:
    """Cost calculation result when cost cannot be calculated."""

    ok: Literal[False]
    model_name: str
    breakdown: tuple[CostComponent, ...]
    total_cost_usd: None
    error_type: str
    error_message: str


CostResult = CostSuccess | CostFailure

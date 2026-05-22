from __future__ import annotations

from typing import TypedDict


class Usage(TypedDict, total=False):
    """Token usage metrics returned by the model provider."""

    prompt_token_count: int | None
    cached_content_token_count: int | None
    thoughts_token_count: int | None
    candidates_token_count: int | None


class CostComponent(TypedDict):
    """Cost breakdown for a single token component."""

    tokens: int
    cost: float


class CostSuccessResult(TypedDict):
    """Successful cost calculation result."""

    model: str
    breakdown: dict[str, CostComponent]
    total_cost_usd: float


class CostErrorResult(TypedDict):
    """Cost calculation result when pricing cannot be resolved."""

    model: str
    error: str
    total_cost_usd: float


CostResult = CostSuccessResult | CostErrorResult

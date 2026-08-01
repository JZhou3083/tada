from dataclasses import dataclass
from typing import Generic, TypeVar

from tada.observability.cost.types import CostResult

T = TypeVar("T")


@dataclass(frozen=True)
class ResponseMetadata:
    """Standardised metadata for all LLM gateway calls."""

    request_id: str
    model_name: str
    elapsed_seconds: float
    cost: CostResult
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class GatewayResponse(Generic[T]):
    """Unified return object for every LLM gateway adapter."""

    content: T
    metadata: ResponseMetadata

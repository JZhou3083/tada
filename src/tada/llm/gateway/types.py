from dataclasses import dataclass
from typing import Generic, TypeVar

from tada.observability.cost.types import CostResult

T = TypeVar("T")


@dataclass(frozen=True)
class ResponseMetadata:
    """Standardised metadata for all LLM gateway calls."""

    model_name: str
    elapsed_second: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: CostResult


@dataclass(frozen=True)
class GatewayResponse(Generic[T]):
    """Unified return object for the VertexAIGateway."""

    content: T
    metadata: ResponseMetadata

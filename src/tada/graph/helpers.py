from decimal import Decimal

from langgraph.config import get_stream_writer

from tada.graph.status import (
    GraphStatusEvent,
    LLMUsage,
    SectionState,
    StatusIssue,
    StatusUpdate,
)
from tada.llm.gateway.types import ResponseMetadata
from tada.observability.cost.types import CostSuccess


def llm_usage_from_metadata(
    metadata: ResponseMetadata | None,
) -> LLMUsage | None:
    if metadata is None:
        return None

    total_tokens = metadata.total_tokens if metadata.total_tokens is not None else 0

    total_cost_usd = (
        metadata.cost.total_cost_usd
        if isinstance(metadata.cost, CostSuccess)
        else Decimal("0")
    )

    return LLMUsage(
        total_tokens=total_tokens,
        total_cost_usd=total_cost_usd,
    )


def emit_graph_status(
    name: str,
    *,
    state: SectionState | None = None,
    attempts: int | None = None,
    issues: tuple[StatusIssue, ...] | None = None,
    llm_response_metadata: ResponseMetadata | None = None,
) -> None:
    """
    Write a partial graph status update to the custom graph stream.

    Patch semantics:
    - state=None preserves current state
    - attempts=None preserves current attempts
    - issues=None preserves current issues
    - issues=() clears current issues
    - issues=(...) replaces current issues
    - llm_response_metadata=None means no usage delta
    """
    writer = get_stream_writer()

    writer(
        GraphStatusEvent(
            section_name=name,
            update=StatusUpdate(
                state=state,
                attempts=attempts,
                issues=issues,
                llm_usage=llm_usage_from_metadata(llm_response_metadata),
            ),
        )
    )

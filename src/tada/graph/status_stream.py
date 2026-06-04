from dataclasses import dataclass
from decimal import Decimal

from langgraph.config import get_stream_writer

from tada.graph.status import (
    GraphStatusEvent,
    IssueSeverity,
    LLMUsage,
    SectionState,
    StatusIssue,
    StatusUpdate,
)
from tada.llm.gateway import ResponseMetadata
from tada.llm.schemas import EvalResult
from tada.observability.cost.types import CostSuccess


@dataclass(frozen=True)
class StatusEmitRequest:
    graph_name: str
    section_name: str
    state: SectionState | None = None
    attempts: int | None = None
    issues: tuple[StatusIssue, ...] | None = None
    llm_response_metadata: ResponseMetadata | None = None


def emit_graph_status(request: StatusEmitRequest) -> None:
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
            graph_name=request.graph_name,
            section_name=request.section_name,
            update=StatusUpdate(
                state=request.state,
                attempts=request.attempts,
                issues=request.issues,
                llm_usage=_llm_usage_from_metadata(request.llm_response_metadata),
            ),
        )
    )


def issues_from_eval_result(eval_result: EvalResult) -> tuple[StatusIssue, ...]:
    issues: list[StatusIssue] = []

    for issue in eval_result.blocking_issues:
        issues.append(
            StatusIssue(
                message=issue.item,
                severity=IssueSeverity.ERROR,
                code=issue.type,
                source="eval",
            )
        )

    for issue in eval_result.non_blocking_issues:
        issues.append(
            StatusIssue(
                message=issue.item,
                severity=IssueSeverity.WARNING,
                code=issue.type,
                source="eval",
            )
        )

    return tuple(issues)


def _llm_usage_from_metadata(
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

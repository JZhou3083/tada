from langgraph.config import get_stream_writer

from tada.graph.events import (
    GraphStatusEvent,
    SectionState,
    StatusIssue,
    StatusUpdate,
    StepKind,
)


def emit_graph_status(
    name: str,
    kind: StepKind,
    *,
    state: SectionState | None = None,
    attempts: int | None = None,
    issues: tuple[StatusIssue, ...] | None = None,
) -> None:
    """
    Write a partial graph status update to the custom graph stream.

    Patch semantics:
    - state=None preserves current state
    - attempts=None preserves current attempts
    - issues=None preserves current issues
    - issues=() clears current issues
    - issues=(...) replaces current issues
    """
    writer = get_stream_writer()

    writer(
        GraphStatusEvent(
            name=name,
            kind=kind,
            update=StatusUpdate(
                state=state,
                attempts=attempts,
                issues=issues,
            ),
        )
    )

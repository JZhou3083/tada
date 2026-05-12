from langgraph.config import get_stream_writer

from tada.graph.events import GraphStatusEvent, SectionState, Status, StepKind


def emit_graph_status(
    name: str, kind: StepKind, state: SectionState, attempts: int = 0
):
    """Write to the custom graph stream, to be consumed for CLI events"""
    writer = get_stream_writer()
    writer(
        GraphStatusEvent(
            name=name,
            kind=kind,
            status=Status(state=state, attempts=attempts),
        )
    )

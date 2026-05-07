from langgraph.config import get_stream_writer

from tada.graph.events import GraphStatusEvent, SectionState, Status


def emit_graph_status(section: str, state: SectionState, attempts: int = 0):
    """Write to the custom graph stream, to be consumed for CLI events"""
    writer = get_stream_writer()
    writer(
        GraphStatusEvent(
            section=section,
            status=Status(state=state, attempts=attempts),
        )
    )

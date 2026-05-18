from typing import Any

from langgraph.graph.state import CompiledStateGraph

from tada.application.ports import StatusSink
from tada.graph.events import GraphStatusEvent


def run_graph_with_status(
    graph: CompiledStateGraph,
    input_state: dict[str, Any],
    *,
    status_sink: StatusSink,
) -> dict[str, Any]:
    final_state: dict[str, Any] | None = None

    for chunk in graph.stream(
        input_state,
        stream_mode=["values", "custom"],
        subgraphs=True,
        version="v2",
    ):
        if chunk["type"] == "custom":
            if isinstance(chunk["data"], GraphStatusEvent):
                status_sink.handle(chunk["data"])

        elif chunk["type"] == "values":
            final_state = chunk["data"]

    if final_state is None:
        raise RuntimeError("Documentation workflow completed without final state")

    return final_state

from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langgraph.graph.state import CompiledStateGraph

from tada.application.ports import StatusSink
from tada.graph.events import GraphStatusEvent


def run_graph_with_status(
    graph: CompiledStateGraph,
    input_state: dict[str, Any],
    *,
    status_sink: StatusSink,
    thread_id: str,
    callbacks: Sequence[BaseCallbackHandler] | None = None,
) -> dict[str, Any]:
    final_state: dict[str, Any] | None = None

    callbacks_list = list(callbacks or [])

    for chunk in graph.stream(
        input_state,
        stream_mode=["values", "custom"],
        subgraphs=True,
        version="v2",
        config={"callbacks": callbacks_list, "configurable": {"thread_id": thread_id}},
    ):
        if chunk["type"] == "custom":
            if isinstance(chunk["data"], GraphStatusEvent):
                status_sink.handle(chunk["data"])

        elif chunk["type"] == "values":
            final_state = chunk["data"]

    if final_state is None:
        raise RuntimeError("Documentation workflow completed without final state")

    return final_state

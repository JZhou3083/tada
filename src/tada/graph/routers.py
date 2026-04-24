from __future__ import annotations

from langgraph.types import Send

from tada.graph.ids import NodeId
from tada.graph.state import State


def route_plan_to_workers(state: State) -> list[Send]:
    return [
        Send(NodeId.SUMMARIZE, {"section_id": section})
        for section in state["generation_plan"]
    ]

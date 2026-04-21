from __future__ import annotations

from tada.graph.state import State, StateUpdate


def mock_llm(state: State) -> StateUpdate:
    return {"response": f"Dummy docs for '{state['workbook'].name}'"}

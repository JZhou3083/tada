from __future__ import annotations

from tada.graph.state import ComponentSummarizerState, StateUpdate


def generate_section_docs(state: ComponentSummarizerState) -> StateUpdate:
    return {"generated_docs": {state["component_id"]: "dummy text"}}

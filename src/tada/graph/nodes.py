from __future__ import annotations

from tada.graph.state import SectionSummarizerState, StateUpdate


def generate_section_docs(state: SectionSummarizerState) -> StateUpdate:
    return {"generated_docs": {state["section_id"]: "dummy text"}}

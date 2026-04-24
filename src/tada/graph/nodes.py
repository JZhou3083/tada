from __future__ import annotations

from tada.graph.state import SectionSummarizerState, StateUpdate


def generate_section_docs(state: SectionSummarizerState) -> StateUpdate:
    section_data = state["section_id"].fetch_from(state["workbook"])

    # TODO: retrieve template based on section id & run generation

    # Mock-up of actual processing
    summary = len(section_data)

    return {"generated_docs": {state["section_id"]: str(summary)}}

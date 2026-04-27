from __future__ import annotations

import logging

from tada.graph.state import SectionSummarizerState, State, StateUpdate

logger = logging.getLogger(__name__)


def generate_section_summary(state: SectionSummarizerState) -> StateUpdate:
    section_data = state["section_id"].fetch_from(state["workbook"])

    # TODO: retrieve template based on section id & run generation

    # Mock-up of actual processing
    summary = len(section_data)

    return {"generated_summaries": {state["section_id"]: str(summary)}}


def compile_summaries(state: State) -> StateUpdate:
    logger.debug("Compiling everything")
    full_summary = "\npagebreak\n".join(state["generated_summaries"].values())
    print(full_summary)
    return {}

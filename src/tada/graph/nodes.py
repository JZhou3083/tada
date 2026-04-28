import logging
import time
from typing import TypedDict

from tada.domain.workbook import WorkbookSection
from tada.graph.state import OutputState, OverallState, SectionSummarizerState

logger = logging.getLogger(__name__)


class SectionSummaryUpdate(TypedDict):
    generated_summaries: dict[WorkbookSection, str]


def generate_section_summary(
    state: SectionSummarizerState,
) -> SectionSummaryUpdate:
    # TODO: retrieve template based on section and run generation

    time.sleep(1)

    return {"generated_summaries": {state["section"]: state["prompt"][:100]}}


def compile_summaries(state: OverallState) -> OutputState:
    summaries = state["generated_summaries"]
    logger.debug("Compiling all %d summaries...", len(summaries))

    ordered = [(s, summaries[s]) for s in state["generation_plan"] if s in summaries]

    formatted_sections = [
        f"# {section.value}\n{summary}" for section, summary in ordered
    ]
    compiled_doc = "\n\n".join(formatted_sections)

    logger.debug("Compiled %d summaries", len(summaries))
    return {"final_doc": compiled_doc}

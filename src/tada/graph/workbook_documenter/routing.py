from langgraph.types import Send

from tada.domain.sections import WorkbookSection
from tada.domain.workbook import Workbook
from tada.graph.workbook_documenter.ids import WorkbookNodeId
from tada.graph.workbook_documenter.state import (
    InputState,
)
from tada.prompts.loader import load_section_documentation_prompts


def _get_section_documenter_payload(section: WorkbookSection, workbook: Workbook):
    prompt, response_template = load_section_documentation_prompts(section)
    return {
        "section": section,
        "data": section.fetch_from(workbook),
        "prompt": prompt,
        "response_template": response_template,
    }


def route_plan_to_documenters(state: InputState) -> list[Send]:
    if not state["generation_plan"]:
        raise ValueError("generation_plan must contain at least one WorkbookSection")

    # De-duplicate plan whilst preserving order
    sections = list(dict.fromkeys(state["generation_plan"]))
    return [
        Send(
            WorkbookNodeId.DOCUMENT_SECTION,
            _get_section_documenter_payload(section, state["workbook"]),
        )
        for section in sections
    ]

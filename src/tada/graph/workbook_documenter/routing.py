import structlog
from langgraph.types import Send

from tada.domain.sections import WorkbookSection
from tada.domain.workbook import Workbook
from tada.graph.ids import GraphId
from tada.graph.workbook_documenter.ids import WorkbookNodeId
from tada.graph.workbook_documenter.payload import normalise_llm_payload
from tada.graph.workbook_documenter.state import (
    WorkbookDocumenterInput,
)
from tada.prompts.loader import load_section_documentation_prompts

_GRAPH_NAME = GraphId.WORKBOOK_DOCUMENTER.value

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__).bind(
    graph_name=_GRAPH_NAME
)


def _get_section_documenter_payload(section: WorkbookSection, workbook: Workbook):
    prompt, response_template = load_section_documentation_prompts(section)
    raw_data = section.fetch_from(workbook)

    return {
        "section": section,
        "data": normalise_llm_payload(raw_data),
        "prompt": prompt,
        "response_template": response_template,
    }


def route_plan_to_documenters(state: WorkbookDocumenterInput) -> list[Send]:
    planned_sections = state["sections_to_document"]

    if not planned_sections:
        logger.error(
            "graph.node.failed",
            node_name="route_plan_to_documenters",
            error_type="ValueError",
            error="sections_to_document must contain at least one WorkbookSection",
        )
        raise ValueError(
            "sections_to_document must contain at least one WorkbookSection"
        )

    # De-duplicate plan whilst preserving order
    sections = list(dict.fromkeys(state["sections_to_document"]))

    logger.debug(
        "graph.edge.traversed",
        edge_name="route_plan_to_documenters",
        source_node="plan",
        target_node=WorkbookNodeId.DOCUMENT_SECTION.value,
        section_count=len(planned_sections),
        deduplicated_section_count=len(sections),
        duplicate_section_count=len(planned_sections) - len(sections),
        sections=[section.value for section in sections],
    )

    return [
        Send(
            WorkbookNodeId.DOCUMENT_SECTION.value,
            _get_section_documenter_payload(section, state["workbook"]),
        )
        for section in sections
    ]

import logging
from enum import StrEnum

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from tada.domain.workbook import Workbook, WorkbookSection
from tada.graph.nodes.summarize import (
    summarize_all_sections_documentation,
)
from tada.graph.state import (
    InputState,
    OutputState,
    OverallState,
)
from tada.graph.workflows.section_subgraph import build_section_documenter_subgraph

logger = logging.getLogger(__name__)


class NodeId(StrEnum):
    DOCUMENT_SECTION = "document_section"
    SUMMARIZE_ALL_SECTION_DOCS = "summarize_all_section_docs"


def _get_section_documenter_payload(section: WorkbookSection, workbook: Workbook):
    prompt, response_template = section.load_documentation_prompts()
    return {
        "section": section,
        "data": section.fetch_from(workbook),
        "prompt": prompt,
        "response_template": response_template,
    }


def route_plan_to_documenters(state: InputState) -> list[Send]:
    if not state["generation_plan"]:
        raise ValueError("generation_plan must contain at least one WorkbookSection")

    return [
        Send(
            NodeId.DOCUMENT_SECTION,
            _get_section_documenter_payload(section, state["workbook"]),
        )
        for section in set(state["generation_plan"])
    ]


def build_documentation_workflow(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Construct and compile the LangGraph workflow for workbook documentation.

    This function creates the workflow definition from scratch and returns a
    compiled graph ready to be invoked.

    Args:
        checkpointer: A checkpoint saver object which will be passed to the graph and
            can be used to persist graph states.

    Returns:
        A compiled LangGraph workflow that accepts a Workbook object and generation plan
            as input.
    """
    builder = StateGraph(
        OverallState, input_schema=InputState, output_schema=OutputState
    )

    builder.add_node(NodeId.DOCUMENT_SECTION, build_section_documenter_subgraph())
    builder.add_node(
        NodeId.SUMMARIZE_ALL_SECTION_DOCS, summarize_all_sections_documentation
    )

    builder.add_conditional_edges(
        START, route_plan_to_documenters, [NodeId.DOCUMENT_SECTION]
    )
    builder.add_edge(NodeId.DOCUMENT_SECTION, NodeId.SUMMARIZE_ALL_SECTION_DOCS)
    builder.add_edge(NodeId.SUMMARIZE_ALL_SECTION_DOCS, END)

    workflow = builder.compile(checkpointer=checkpointer)
    logger.debug("Workflow compiled:\n%s", workflow.get_graph().draw_ascii())
    return workflow

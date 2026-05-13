import logging

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from tada.graph.section_documenter.graph import build_section_documenter_subgraph
from tada.graph.workbook_documenter.ids import WorkbookNodeId
from tada.graph.workbook_documenter.nodes import (
    summarize_all_sections_documentation,
)
from tada.graph.workbook_documenter.routing import route_plan_to_documenters
from tada.graph.workbook_documenter.state import (
    InputState,
    OutputState,
    OverallState,
)

logger = logging.getLogger(__name__)


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

    builder.add_node(
        WorkbookNodeId.DOCUMENT_SECTION, build_section_documenter_subgraph()
    )
    builder.add_node(
        WorkbookNodeId.SUMMARIZE_ALL_SECTION_DOCS, summarize_all_sections_documentation
    )

    builder.add_conditional_edges(
        START, route_plan_to_documenters, [WorkbookNodeId.DOCUMENT_SECTION]
    )
    builder.add_edge(
        WorkbookNodeId.DOCUMENT_SECTION, WorkbookNodeId.SUMMARIZE_ALL_SECTION_DOCS
    )
    builder.add_edge(WorkbookNodeId.SUMMARIZE_ALL_SECTION_DOCS, END)

    workflow = builder.compile(checkpointer=checkpointer)
    logger.debug("Workflow compiled:\n%s", workflow.get_graph().draw_ascii())
    return workflow

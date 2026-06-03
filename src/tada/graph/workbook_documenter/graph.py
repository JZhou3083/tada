import logging
from typing import TypeAlias

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from tada.graph.config import GraphContext
from tada.graph.section_documenter.graph import build_section_documenter_subgraph
from tada.graph.workbook_documenter.ids import WorkbookNodeId
from tada.graph.workbook_documenter.nodes import (
    summarize_all_sections_documentation,
)
from tada.graph.workbook_documenter.routing import route_plan_to_documenters
from tada.graph.workbook_documenter.state import (
    WorkbookDocumenterInput,
    WorkbookDocumenterOutput,
    WorkbookDocumenterState,
)

logger = logging.getLogger(__name__)


WorkbookDocumenterGraph: TypeAlias = CompiledStateGraph[
    WorkbookDocumenterState,
    GraphContext,
    WorkbookDocumenterInput,
    WorkbookDocumenterOutput,
]


def build_documentation_workflow(
    checkpointer: BaseCheckpointSaver | None = None,
) -> WorkbookDocumenterGraph:
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
        WorkbookDocumenterState,
        context_schema=GraphContext,
        input_schema=WorkbookDocumenterInput,
        output_schema=WorkbookDocumenterOutput,
    )

    builder.add_node(
        WorkbookNodeId.DOCUMENT_SECTION.value, build_section_documenter_subgraph()
    )
    builder.add_node(
        WorkbookNodeId.SUMMARIZE_ALL_SECTION_DOCS.value,
        summarize_all_sections_documentation,
    )

    builder.add_conditional_edges(
        START, route_plan_to_documenters, [WorkbookNodeId.DOCUMENT_SECTION.value]
    )
    builder.add_edge(
        WorkbookNodeId.DOCUMENT_SECTION.value,
        WorkbookNodeId.SUMMARIZE_ALL_SECTION_DOCS.value,
    )
    builder.add_edge(WorkbookNodeId.SUMMARIZE_ALL_SECTION_DOCS.value, END)

    workflow = builder.compile(checkpointer=checkpointer)

    return workflow

import logging
from enum import StrEnum

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from tada.graph.nodes import compile_summaries, generate_section_summary
from tada.graph.state import InputState, OutputState, OverallState

logger = logging.getLogger(__name__)


class NodeId(StrEnum):
    SUMMARIZE_SECTION = "summarize_section"
    COMPILE_SUMMARIES = "compile_summaries"


def route_plan_to_workers(state: InputState) -> list[Send]:
    if not state["generation_plan"]:
        raise ValueError("generation_plan must contain at least one WorkbookSection")

    return [
        Send(
            NodeId.SUMMARIZE_SECTION,
            {"section": section, "section_data": section.fetch_from(state["workbook"])},
        )
        for section in state["generation_plan"]
    ]


def build_documentation_workflow(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Construct and compile the LangGraph workflow for workbook documentation.

    This function creates the workflow definition from scratch and returns a
    compiled graph ready to be invoked with a ``State`` payload.

    Args:
        checkpointer: A checkpoint saver object which will be passed to the graph and
            can be used to persist graph states.

    Returns:
        A compiled LangGraph workflow that accepts ``State`` as input.
    """
    builder = StateGraph(
        OverallState, input_schema=InputState, output_schema=OutputState
    )

    builder.add_node(NodeId.SUMMARIZE_SECTION, generate_section_summary)
    builder.add_node(NodeId.COMPILE_SUMMARIES, compile_summaries)

    builder.add_conditional_edges(
        START, route_plan_to_workers, [NodeId.SUMMARIZE_SECTION]
    )
    builder.add_edge(NodeId.SUMMARIZE_SECTION, NodeId.COMPILE_SUMMARIES)
    builder.add_edge(NodeId.COMPILE_SUMMARIES, END)

    workflow = builder.compile(checkpointer=checkpointer)
    logger.debug("Workflow compiled:\n%s", workflow.get_graph().draw_ascii())
    return workflow

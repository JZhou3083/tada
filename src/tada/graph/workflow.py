import logging
from enum import StrEnum

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from tada.domain.workbook import Workbook, WorkbookSection
from tada.graph.nodes import (
    compile_summaries,
    emit_section_documentation,
    evaluate_section_documentation,
    generate_section_documentation,
)
from tada.graph.state import (
    InputState,
    OutputState,
    OverallState,
    SectionDocumenterState,
)

logger = logging.getLogger(__name__)

MAX_SECTION_ATTEMPTS = 2


class NodeId(StrEnum):
    DOCUMENT_SECTION = "document_section"
    EVALUATE_SECTION_DOCS = "evaluate_section_docs"
    EMIT_SECTION_DOCS = "emit_section_docs"
    COMPILE_SUMMARIES = "compile_summaries"


def route_evaluation_results(state: SectionDocumenterState) -> NodeId:
    if "evaluation_history" not in state:
        raise ValueError("No evaluation to route")

    latest_eval = state["evaluation_history"][-1]

    if latest_eval.passed:
        logger.debug(
            "Emitting documentation for %s attempt=%d non_blocking_issues=%d",
            state["section"].value,
            state["attempts"],
            len(latest_eval.non_blocking_issues),
        )
        return NodeId.EMIT_SECTION_DOCS
    elif state["attempts"] > MAX_SECTION_ATTEMPTS:
        logger.debug(
            "Hit maximum attempts for %s attempt=%d blocking_issues=%d non_blocking_issues=%d",
            state["section"].value,
            state["attempts"],
            len(latest_eval.blocking_issues),
            len(latest_eval.non_blocking_issues),
        )
        return NodeId.EMIT_SECTION_DOCS

    logger.debug(
        "Retrying documentation for %s attempt=%d blocking_issues=%d non_blocking_issues=%d",
        state["section"].value,
        state["attempts"],
        len(latest_eval.blocking_issues),
        len(latest_eval.non_blocking_issues),
    )
    return NodeId.DOCUMENT_SECTION


def _get_section_summarizer_payload(section: WorkbookSection, workbook: Workbook):
    prompt, response_template = section.load_summarization_prompts()
    return {
        "section": section,
        "data": section.fetch_from(workbook),
        "prompt": prompt,
        "response_template": response_template,
        "attempts": 0,
    }


def route_plan_to_summarizers(state: InputState) -> list[Send]:
    if not state["generation_plan"]:
        raise ValueError("generation_plan must contain at least one WorkbookSection")

    return [
        Send(
            NodeId.DOCUMENT_SECTION,
            _get_section_summarizer_payload(section, state["workbook"]),
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

    builder.add_node(NodeId.DOCUMENT_SECTION, generate_section_documentation)
    builder.add_node(NodeId.EVALUATE_SECTION_DOCS, evaluate_section_documentation)
    builder.add_node(NodeId.EMIT_SECTION_DOCS, emit_section_documentation)
    builder.add_node(NodeId.COMPILE_SUMMARIES, compile_summaries)

    builder.add_conditional_edges(
        START, route_plan_to_summarizers, [NodeId.DOCUMENT_SECTION]
    )
    builder.add_edge(NodeId.DOCUMENT_SECTION, NodeId.EVALUATE_SECTION_DOCS)
    builder.add_conditional_edges(
        NodeId.EVALUATE_SECTION_DOCS,
        route_evaluation_results,
        [NodeId.EMIT_SECTION_DOCS, NodeId.DOCUMENT_SECTION],
    )
    builder.add_edge(NodeId.EMIT_SECTION_DOCS, NodeId.COMPILE_SUMMARIES)
    builder.add_edge(NodeId.COMPILE_SUMMARIES, END)

    workflow = builder.compile(checkpointer=checkpointer)
    logger.debug("Workflow compiled:\n%s", workflow.get_graph().draw_ascii())
    return workflow

import logging
from enum import StrEnum
from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from tada.graph.config import MAX_SECTION_ATTEMPTS
from tada.graph.nodes.section import (
    emit_section_documentation,
    evaluate_section_documentation,
    generate_section_documentation,
)
from tada.graph.state import (
    SectionDocumenterInput,
    SectionDocumenterOutput,
    SectionDocumenterState,
)

logger = logging.getLogger(__name__)


class SectionNodeId(StrEnum):
    DOCUMENT_SECTION = "document_section"
    EVALUATE_SECTION_DOCS = "evaluate_section_docs"
    EMIT_SECTION_DOCS = "emit_section_docs"


def route_evaluation_results(state: SectionDocumenterState) -> Literal["emit", "retry"]:
    if "evaluation_history" not in state:
        raise ValueError("No evaluation to route")

    latest_eval = state["evaluation_history"][-1]

    if latest_eval.passed:
        logger.debug(
            "Emitting documentation for %s attempt=%d non_blocking_issues=%d",
            state["section"].value,
            state["generation_attempts"],
            len(latest_eval.non_blocking_issues),
        )
        return "emit"

    elif state["generation_attempts"] > MAX_SECTION_ATTEMPTS:
        logger.debug(
            "Hit maximum attempts for %s attempt=%d blocking_issues=%d non_blocking_issues=%d",
            state["section"].value,
            state["generation_attempts"],
            len(latest_eval.blocking_issues),
            len(latest_eval.non_blocking_issues),
        )
        return "emit"

    logger.debug(
        "Retrying documentation for %s attempt=%d blocking_issues=%d non_blocking_issues=%d",
        state["section"].value,
        state["generation_attempts"],
        len(latest_eval.blocking_issues),
        len(latest_eval.non_blocking_issues),
    )
    return "retry"


def build_section_documenter_subgraph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:

    builder = StateGraph(
        SectionDocumenterState,
        input_schema=SectionDocumenterInput,
        output_schema=SectionDocumenterOutput,
    )

    builder.add_node(SectionNodeId.DOCUMENT_SECTION, generate_section_documentation)
    builder.add_node(
        SectionNodeId.EVALUATE_SECTION_DOCS, evaluate_section_documentation
    )
    builder.add_node(SectionNodeId.EMIT_SECTION_DOCS, emit_section_documentation)

    builder.add_edge(START, SectionNodeId.DOCUMENT_SECTION)
    builder.add_edge(
        SectionNodeId.DOCUMENT_SECTION, SectionNodeId.EVALUATE_SECTION_DOCS
    )
    builder.add_conditional_edges(
        SectionNodeId.EVALUATE_SECTION_DOCS,
        route_evaluation_results,
        {
            "emit": SectionNodeId.EMIT_SECTION_DOCS,
            "retry": SectionNodeId.DOCUMENT_SECTION,
        },
    )
    builder.add_edge(SectionNodeId.EMIT_SECTION_DOCS, END)

    workflow = builder.compile(checkpointer=checkpointer)
    logger.debug(
        "Section documenting workflow compiled:\n%s", workflow.get_graph().draw_ascii()
    )
    return workflow

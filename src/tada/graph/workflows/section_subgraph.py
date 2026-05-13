import logging
from enum import StrEnum
from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from tada.graph.config import MAX_SECTION_ATTEMPTS
from tada.graph.nodes.section import (
    emit_section_documentation,
    emit_section_documentation_retry_limit,
    emit_section_documentation_skipped,
    evaluate_section_documentation,
    generate_section_documentation,
    prepare_section,
)
from tada.graph.state import (
    SectionDocumenterInput,
    SectionDocumenterOutput,
    SectionDocumenterState,
    get_latest_eval_result,
)

logger = logging.getLogger(__name__)


class SectionNodeId(StrEnum):
    PREPARE_SECTION = "prepare_section"
    GENERATE_SECTION_DOCS = "generate_section_docs"
    EVALUATE_SECTION_DOCS = "evaluate_section_docs"
    EMIT_SECTION_DOCS = "emit_section_docs"
    EMIT_SECTION_DOCS_AFTER_RETRY_LIMIT = "emit_section_docs_after_retry_limit"
    EMIT_SECTION_DOCS_SKIPPED = "emit_section_docs_skipped"


def route_after_precheck(state: SectionDocumenterState) -> Literal["skip", "generate"]:
    return "skip" if state.get("skip_section") else "generate"


def route_evaluation_results(
    state: SectionDocumenterState,
) -> Literal["emit", "emit_with_issues", "retry"]:
    latest_eval = get_latest_eval_result(state)
    if latest_eval is None:
        raise ValueError("No evaluation to route")

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
        return "emit_with_issues"

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

    builder.add_node(SectionNodeId.PREPARE_SECTION, prepare_section)
    builder.add_node(
        SectionNodeId.GENERATE_SECTION_DOCS, generate_section_documentation
    )
    builder.add_node(
        SectionNodeId.EVALUATE_SECTION_DOCS, evaluate_section_documentation
    )
    builder.add_node(SectionNodeId.EMIT_SECTION_DOCS, emit_section_documentation)
    builder.add_node(
        SectionNodeId.EMIT_SECTION_DOCS_AFTER_RETRY_LIMIT,
        emit_section_documentation_retry_limit,
    )
    builder.add_node(
        SectionNodeId.EMIT_SECTION_DOCS_SKIPPED,
        emit_section_documentation_skipped,
    )

    builder.add_edge(START, SectionNodeId.PREPARE_SECTION)
    builder.add_conditional_edges(
        SectionNodeId.PREPARE_SECTION,
        route_after_precheck,
        {
            "skip": SectionNodeId.EMIT_SECTION_DOCS_SKIPPED,
            "generate": SectionNodeId.GENERATE_SECTION_DOCS,
        },
    )
    builder.add_edge(
        SectionNodeId.GENERATE_SECTION_DOCS, SectionNodeId.EVALUATE_SECTION_DOCS
    )
    builder.add_conditional_edges(
        SectionNodeId.EVALUATE_SECTION_DOCS,
        route_evaluation_results,
        {
            "emit": SectionNodeId.EMIT_SECTION_DOCS,
            "emit_with_issues": SectionNodeId.EMIT_SECTION_DOCS_AFTER_RETRY_LIMIT,
            "retry": SectionNodeId.GENERATE_SECTION_DOCS,
        },
    )
    builder.add_edge(SectionNodeId.EMIT_SECTION_DOCS, END)
    builder.add_edge(SectionNodeId.EMIT_SECTION_DOCS_AFTER_RETRY_LIMIT, END)
    builder.add_edge(SectionNodeId.EMIT_SECTION_DOCS_SKIPPED, END)

    workflow = builder.compile(checkpointer=checkpointer)
    logger.debug(
        "Section documenting workflow compiled:\n%s", workflow.get_graph().draw_ascii()
    )
    return workflow

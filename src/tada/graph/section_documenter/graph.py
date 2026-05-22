import logging

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from tada.graph.section_documenter.ids import SectionNodeId
from tada.graph.section_documenter.nodes import (
    emit_section_documentation,
    emit_section_documentation_retry_limit,
    emit_section_documentation_skipped,
    evaluate_section_documentation,
    generate_section_documentation,
    prepare_section,
)
from tada.graph.section_documenter.routing import (
    route_after_precheck,
    route_evaluation_results,
)
from tada.graph.section_documenter.state import (
    SectionDocumenterInput,
    SectionDocumenterOutput,
    SectionDocumenterState,
)

logger = logging.getLogger(__name__)


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

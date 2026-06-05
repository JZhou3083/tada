from typing import TypeAlias

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from tada.graph.section_documenter.context import SectionDocumenterContext
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

SectionDocumenterGraph: TypeAlias = CompiledStateGraph[
    SectionDocumenterState,
    SectionDocumenterContext,
    SectionDocumenterInput,
    SectionDocumenterOutput,
]


def build_section_documenter_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> SectionDocumenterGraph:

    builder = StateGraph(
        SectionDocumenterState,
        context_schema=SectionDocumenterContext,
        input_schema=SectionDocumenterInput,
        output_schema=SectionDocumenterOutput,
    )

    builder.add_node(SectionNodeId.PREPARE_SECTION.value, prepare_section)
    builder.add_node(
        SectionNodeId.GENERATE_SECTION_DOCS.value,
        generate_section_documentation,
    )
    builder.add_node(
        SectionNodeId.EVALUATE_SECTION_DOCS.value,
        evaluate_section_documentation,
    )
    builder.add_node(SectionNodeId.EMIT_SECTION_DOCS.value, emit_section_documentation)
    builder.add_node(
        SectionNodeId.EMIT_SECTION_DOCS_AFTER_RETRY_LIMIT.value,
        emit_section_documentation_retry_limit,
    )
    builder.add_node(
        SectionNodeId.EMIT_SECTION_DOCS_SKIPPED.value,
        emit_section_documentation_skipped,
    )

    builder.add_edge(START, SectionNodeId.PREPARE_SECTION.value)
    builder.add_conditional_edges(
        SectionNodeId.PREPARE_SECTION.value,
        route_after_precheck,
        {
            "skip": SectionNodeId.EMIT_SECTION_DOCS_SKIPPED.value,
            "generate": SectionNodeId.GENERATE_SECTION_DOCS.value,
        },
    )
    builder.add_edge(
        SectionNodeId.GENERATE_SECTION_DOCS.value,
        SectionNodeId.EVALUATE_SECTION_DOCS.value,
    )
    builder.add_conditional_edges(
        SectionNodeId.EVALUATE_SECTION_DOCS.value,
        route_evaluation_results,
        {
            "emit": SectionNodeId.EMIT_SECTION_DOCS.value,
            "emit_with_issues": SectionNodeId.EMIT_SECTION_DOCS_AFTER_RETRY_LIMIT.value,
            "retry": SectionNodeId.GENERATE_SECTION_DOCS.value,
        },
    )
    builder.add_edge(SectionNodeId.EMIT_SECTION_DOCS.value, END)
    builder.add_edge(SectionNodeId.EMIT_SECTION_DOCS_AFTER_RETRY_LIMIT.value, END)
    builder.add_edge(SectionNodeId.EMIT_SECTION_DOCS_SKIPPED.value, END)

    workflow = builder.compile(checkpointer=checkpointer)

    return workflow

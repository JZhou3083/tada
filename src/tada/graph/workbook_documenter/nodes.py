from importlib import resources

import structlog
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes

from tada.domain.sections import WorkbookSection
from tada.graph.config import AI_NOTICE
from tada.graph.events import SectionState
from tada.graph.helpers import emit_graph_status
from tada.graph.workbook_documenter.state import OutputState, OverallState
from tada.llm.configs import build_base_generation_config
from tada.llm.gateway import get_vertexai_gateway
from tada.observability.otel.observe import observe

logger: structlog.stdlib.BoundLogger = structlog.get_logger("tada")


# Section order is mirrored from doc-agent repo config.yaml
# TODO: investigate whether we actually need to pass the summariser all sections
SECTION_ORDER = [
    WorkbookSection.DATASOURCES,
    WorkbookSection.CALCULATIONS,
    WorkbookSection.DASHBOARDS,
    WorkbookSection.WORKSHEETS,
    WorkbookSection.ACTIONS,
    WorkbookSection.PARAMETERS,
    WorkbookSection.TABLES,
]


@observe(
    "graph.node.summarize_all_sections_documentation",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
    },
)
def summarize_all_sections_documentation(state: OverallState) -> OutputState:
    node_name = "summarize_all_sections_documentation"
    docs_by_section = state["docs_by_section"]
    run_summary_step = state["run_summary_step"]

    logger.info(
        "graph.node.started",
        node_name=node_name,
        section_doc_count=len(docs_by_section),
        summary_enabled=run_summary_step,
    )

    ordered_section_docs = [
        docs_by_section[s] for s in SECTION_ORDER if s in docs_by_section
    ]
    compiled_doc = "\\pagebreak\n\n".join(ordered_section_docs)

    logger.info(
        "graph.document.compiled",
        node_name=node_name,
        section_doc_count=len(docs_by_section),
        ordered_section_doc_count=len(ordered_section_docs),
        compiled_doc_chars=len(compiled_doc),
    )

    final_doc_parts = ordered_section_docs

    if not state["run_summary_step"]:
        emit_graph_status(
            name="summary",
            state=SectionState.SKIPPED,
        )

        logger.info(
            "graph.node.skipped",
            node_name=node_name,
            skipped_step="summary_generation",
            skip_reason="summary_step_disabled",
            section_doc_count=len(docs_by_section),
        )

    else:
        emit_graph_status(
            name="summary",
            state=SectionState.GENERATING,
        )

        summariser_prompt = (
            resources.files("tada") / "prompts" / "summariser.md"
        ).read_text(encoding="utf-8")

        gateway = get_vertexai_gateway()

        response = gateway.generate_text(
            model="gemini-3-flash-preview",
            contents=[summariser_prompt, compiled_doc],
            config=build_base_generation_config(),
        )

        logger.info(
            "graph.summary.generated",
            node_name=node_name,
            model_name=response.metadata.model_name,
            elapsed_seconds=response.metadata.elapsed_seconds,
            input_tokens=response.metadata.input_tokens,
            output_tokens=response.metadata.output_tokens,
            total_tokens=response.metadata.total_tokens,
        )

        # Update live display with token usage and cost info
        emit_graph_status(
            name="summary",
            state=SectionState.DONE,
            llm_response_metadata=response.metadata,
        )

        final_doc_parts = [response.content] + ordered_section_docs

    final_doc = "\n\n".join([p.rstrip() for p in [AI_NOTICE] + final_doc_parts])

    logger.info(
        "graph.node.completed",
        node_name=node_name,
        section_doc_count=len(docs_by_section),
        ordered_section_doc_count=len(ordered_section_docs),
        summary_enabled=run_summary_step,
        final_doc_chars=len(final_doc),
    )

    return {"final_doc": final_doc}

import structlog
from langgraph.runtime import Runtime
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes

from tada.domain.sections import WorkbookSection
from tada.graph.helpers import emit_graph_status
from tada.graph.schemas import LLMCallEvent
from tada.graph.status import IssueSeverity, SectionState, StatusIssue
from tada.graph.workbook_documenter.context import WorkbookDocumenterContext
from tada.graph.workbook_documenter.document_markdown import AI_GENERATED_NOTICE_MD
from tada.graph.workbook_documenter.state import (
    WorkbookDocumenterOutput,
    WorkbookDocumenterState,
)
from tada.llm.configs import build_base_generation_config
from tada.observability.otel.observe import observe
from tada.prompts import load_prompt

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

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
def summarize_all_sections_documentation(
    state: WorkbookDocumenterState, runtime: Runtime[WorkbookDocumenterContext]
) -> WorkbookDocumenterOutput:
    node_name = "summarize_all_sections_documentation"
    docs_by_section = state["docs_by_section"]
    include_summary = state["include_summary"]

    logger.info(
        "graph.node.started",
        node_name=node_name,
        section_doc_count=len(docs_by_section),
        summary_enabled=include_summary,
    )

    ordered_section_docs = [
        docs_by_section[s] for s in SECTION_ORDER if s in docs_by_section
    ]

    # Skip the summary step if specified in the run config
    if not state["include_summary"]:
        emit_graph_status(
            name="summary",
            state=SectionState.SKIPPED,
            attempts=0,
        )
        logger.info(
            "graph.node.skipped",
            node_name=node_name,
            skipped_step="summary_generation",
            skip_reason="summary_step_disabled",
            section_doc_count=len(docs_by_section),
        )

        llm_calls_update = []
        final_doc_parts = ordered_section_docs

    # Skip the summary step if no documentation was generated to summarize e.g. alll
    # specified sections were skipped due to being empty.
    elif not ordered_section_docs:
        emit_graph_status(
            name="summary",
            state=SectionState.SKIPPED,
            attempts=0,
            issues=(
                StatusIssue(
                    "Summary skipped because no section documentation was generated.",
                    severity=IssueSeverity.INFO,
                    code="empty-document",
                    source="graph",
                ),
            ),
        )
        logger.info(
            "graph.node.skipped",
            node_name=node_name,
            skipped_step="summary_generation",
            skip_reason="empty_section_docs",
            section_doc_count=len(docs_by_section),
        )

        llm_calls_update = []
        final_doc_parts = [
            "\n\n_No documentation was generated because all selected sections were empty or skipped._"
        ]

    else:
        emit_graph_status(name="summary", state=SectionState.GENERATING, attempts=1)

        summariser_prompt = load_prompt("summariser.md")

        model_name = runtime.context.workbook_settings.summary_model
        compiled_parts = "\n---\n".join(ordered_section_docs)

        try:
            response = runtime.context.gateway.generate_text(
                model=model_name,
                contents=[summariser_prompt, compiled_parts],
                config=build_base_generation_config(),
            )
        except Exception as exc:
            logger.error(
                "graph.node.failed",
                node_name=node_name,
                section=None,
                attempt=1,
                failure_stage="llm_summary_generation",
                model_name=model_name,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                section_doc_count=len(docs_by_section),
                ordered_section_doc_count=len(ordered_section_docs),
                compiled_doc_chars=len(compiled_parts),
                summariser_prompt_chars=len(summariser_prompt),
                exc_info=True,
            )

            emit_graph_status(
                name="summary",
                state=SectionState.FAILED,
                attempts=1,
                issues=(
                    StatusIssue(
                        message=str(exc),
                        severity=IssueSeverity.ERROR,
                        code=type(exc).__name__,
                        source="llm_gateway",
                    ),
                ),
            )
            raise

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
        llm_calls_update = [
            LLMCallEvent(
                node_name="summarize_all_sections_documentation",
                metadata=response.metadata,
            )
        ]

    final_doc = "\n---\n".join(
        [p.rstrip() for p in [AI_GENERATED_NOTICE_MD] + final_doc_parts]
    )

    logger.info(
        "graph.node.completed",
        node_name=node_name,
        section_doc_count=len(docs_by_section),
        ordered_section_doc_count=len(ordered_section_docs),
        summary_enabled=include_summary,
        final_doc_chars=len(final_doc),
    )

    return {"final_doc": final_doc, "llm_calls": llm_calls_update}

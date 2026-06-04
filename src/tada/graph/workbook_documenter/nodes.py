import structlog
from langgraph.runtime import Runtime
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes

from tada.domain.sections import WorkbookSection
from tada.graph.ids import GraphName
from tada.graph.schemas import LLMCallRecord
from tada.graph.status import (
    IssueSeverity,
    SectionState,
    StatusIssue,
)
from tada.graph.status_stream import StatusEmitRequest, emit_graph_status
from tada.graph.workbook_documenter.context import WorkbookDocumenterContext
from tada.graph.workbook_documenter.document_markdown import AI_GENERATED_NOTICE_MD
from tada.graph.workbook_documenter.ids import WorkbookNodeId
from tada.graph.workbook_documenter.state import (
    WorkbookDocumenterOutput,
    WorkbookDocumenterState,
)
from tada.llm.configs import build_base_generation_config
from tada.observability.otel.observe import observe
from tada.prompts import load_prompt

_GRAPH_NAME = GraphName.WORKBOOK_DOCUMENTER.value

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__).bind(
    graph_name=_GRAPH_NAME
)


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
    f"graph.node.{WorkbookNodeId.SUMMARIZE_ALL_SECTION_DOCS.value}",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
    },
)
def summarize_all_sections_documentation(
    state: WorkbookDocumenterState, runtime: Runtime[WorkbookDocumenterContext]
) -> WorkbookDocumenterOutput:
    node_name = WorkbookNodeId.SUMMARIZE_ALL_SECTION_DOCS.value
    attempt = 1

    docs_by_section = state["docs_by_section"]
    include_summary = state["include_summary"]

    log = logger.bind(node_name=node_name, attempt=attempt)

    log.info(
        "graph.node.started",
        section_doc_count=len(docs_by_section),
        summary_enabled=include_summary,
    )

    ordered_section_docs = [
        docs_by_section[s] for s in SECTION_ORDER if s in docs_by_section
    ]

    # Skip the summary step if specified in the run config
    if not state["include_summary"]:
        emit_graph_status(
            StatusEmitRequest(
                graph_name=_GRAPH_NAME,
                section_name="summary",
                state=SectionState.SKIPPED,
                attempt=1,
            )
        )
        log.info(
            "graph.node.skipped",
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
            StatusEmitRequest(
                graph_name=_GRAPH_NAME,
                section_name="summary",
                state=SectionState.SKIPPED,
                attempt=attempt,
                issues=(
                    StatusIssue(
                        "Summary skipped because no section documentation was generated.",
                        severity=IssueSeverity.INFO,
                        code="empty-document",
                        source="graph",
                    ),
                ),
            )
        )
        log.info(
            "graph.node.skipped",
            skipped_step="summary_generation",
            skip_reason="empty_section_docs",
            section_doc_count=len(docs_by_section),
        )

        llm_calls_update = []
        final_doc_parts = [
            "\n\n_No documentation was generated because all selected sections were empty or skipped._"
        ]

    else:
        emit_graph_status(
            StatusEmitRequest(
                graph_name=_GRAPH_NAME,
                section_name="summary",
                state=SectionState.GENERATING,
                attempt=attempt,
            )
        )

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
            log.error(
                "graph.node.failed",
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
                StatusEmitRequest(
                    graph_name=_GRAPH_NAME,
                    section_name="summary",
                    state=SectionState.FAILED,
                    attempt=attempt,
                    issues=(
                        StatusIssue(
                            message=str(exc),
                            severity=IssueSeverity.ERROR,
                            code=type(exc).__name__,
                            source="llm_gateway",
                        ),
                    ),
                )
            )
            raise

        log.info(
            "graph.summary.generated",
            model_name=response.metadata.model_name,
            elapsed_seconds=response.metadata.elapsed_seconds,
            input_tokens=response.metadata.input_tokens,
            output_tokens=response.metadata.output_tokens,
            total_tokens=response.metadata.total_tokens,
        )

        # Update live display with token usage and cost info
        emit_graph_status(
            StatusEmitRequest(
                graph_name=_GRAPH_NAME,
                section_name="summary",
                state=SectionState.DONE,
                llm_response_metadata=response.metadata,
            )
        )

        final_doc_parts = [response.content] + ordered_section_docs
        llm_calls_update = [
            LLMCallRecord(
                graph_name=_GRAPH_NAME,
                node_name="summarize_all_sections_documentation",
                metadata=response.metadata,
            )
        ]

    final_doc = "\n---\n".join(
        [p.rstrip() for p in [AI_GENERATED_NOTICE_MD] + final_doc_parts]
    )

    log.info(
        "graph.node.completed",
        section_doc_count=len(docs_by_section),
        ordered_section_doc_count=len(ordered_section_docs),
        summary_enabled=include_summary,
        final_doc_chars=len(final_doc),
    )

    return {"final_doc": final_doc, "llm_calls": llm_calls_update}

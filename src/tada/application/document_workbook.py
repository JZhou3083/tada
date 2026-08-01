from dataclasses import dataclass
from pathlib import Path

import structlog
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes

from tada.application.graph_runner import run_workbook_documenter_graph_with_status
from tada.application.ports import NullStatusSink, StatusSink
from tada.domain.sections import WorkbookSection
from tada.domain.workbook import Workbook
from tada.graph import LLMCallRecord, WorkbookDocumenterContext
from tada.graph.workbook_documenter import (
    build_workbook_documenter_graph,
)
from tada.llm.gateway import get_gateway
from tada.observability.otel.observe import observe
from tada.settings import get_settings

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DocumentWorkbookRequest:
    workbook_path: Path
    output_path: Path
    sections: list[WorkbookSection]
    include_summary: bool = True
    # save_artifacts: bool = False, # equivalent of debug


@dataclass(frozen=True)
class DocumentWorkbookRunConfig:
    run_id: str
    debug: bool = False
    artifacts_dir: Path | None = None
    checkpoints_path: Path | None = None


@dataclass(frozen=True)
class DocumentWorkbookResult:
    output_path: Path
    final_doc: str
    llm_calls: list[LLMCallRecord]


@observe(
    "app.document_workbook",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
    },
)
def document_workbook(
    request: DocumentWorkbookRequest,
    *,
    run_config: DocumentWorkbookRunConfig,
    status_sink: StatusSink | None = None,
) -> DocumentWorkbookResult:
    """Generate Markdown documentation for a Tableau workbook.

    This function resolves invokes the documentation workflow, and writes the generated
    documentation to disk.
    """
    logger.debug(
        "app.document_workbook.started",
        workbook_path=str(request.workbook_path),
        output_path=str(request.output_path),
        section_count=len(request.sections),
        include_summary=request.include_summary,
    )

    sink = status_sink or NullStatusSink()

    # Pre-process the workbook using our pre-existing XML -> JSON parsing approach
    workbook = Workbook.from_file(request.workbook_path)
    logger.info(
        "app.document_workbook.workbook.parsed",
        workbook_path=str(request.workbook_path),
    )

    if run_config.debug and run_config.artifacts_dir:
        run_config.artifacts_dir.mkdir(parents=True, exist_ok=True)
        workbook.write_debug(run_config.artifacts_dir)
        logger.info(
            "app.document_workbook.artifacts.saved",
            artifacts_dir=str(run_config.artifacts_dir),
        )

    # if run_config.checkpoints_path:
    #     checkpointer = SqliteSaver(sqlite3.connect(run_config.checkpoints_path))
    #     workflow = build_documentation_workflow(checkpointer=checkpointer)
    # else:
    # TODO: fix checkpointer
    workflow = build_workbook_documenter_graph()

    logger.info(
        "app.document_workbook.workflow.started",
        run_id=run_config.run_id,
    )

    app_settings = get_settings()
    gateway = get_gateway()
    graph_context = WorkbookDocumenterContext(
        gateway=gateway,
        section_settings=app_settings.graph.section_documenter,
        workbook_settings=app_settings.graph.workbook_documenter,
    )

    final_state = run_workbook_documenter_graph_with_status(
        graph=workflow,
        input={
            "workbook": workbook,
            "sections_to_document": request.sections,
            "include_summary": request.include_summary,
        },
        context=graph_context,
        status_sink=sink,
    )

    logger.info(
        "app.document_workbook.workflow.completed",
        run_id=run_config.run_id,
    )

    final_doc = final_state["final_doc"]
    llm_calls = final_state["llm_calls"]

    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    request.output_path.write_text(final_doc, encoding="utf-8")

    logger.info(
        "app.document_workbook.output.saved", output_path=str(request.output_path)
    )
    logger.info(
        "app.document_workbook.completed",
        output_path=str(request.output_path),
        run_id=run_config.run_id,
    )

    return DocumentWorkbookResult(
        output_path=request.output_path, final_doc=final_doc, llm_calls=llm_calls
    )

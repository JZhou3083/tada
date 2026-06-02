from dataclasses import dataclass
from pathlib import Path

import structlog
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes

from tada.application.graph_runner import run_graph_with_status
from tada.application.ports import NullStatusSink, StatusSink
from tada.domain.sections import WorkbookSection
from tada.domain.workbook import Workbook
from tada.graph.workbook_documenter.graph import build_documentation_workflow
from tada.observability.otel.observe import observe

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DocumentWorkbookRequest:
    workbook_path: Path
    output_path: Path
    sections: list[WorkbookSection]
    run_summary_step: bool = True
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
        run_summary_step=request.run_summary_step,
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
    workflow = build_documentation_workflow()

    logger.info(
        "app.document_workbook.workflow.started",
        run_id=run_config.run_id,
    )

    final_state = run_graph_with_status(
        graph=workflow,
        input_state={
            "workbook": workbook,
            "generation_plan": request.sections,
            "run_summary_step": request.run_summary_step,
        },
        status_sink=sink,
        thread_id=run_config.run_id,
    )

    logger.info(
        "app.document_workbook.workflow.completed",
        run_id=run_config.run_id,
    )

    final_doc = final_state["final_doc"]

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
        output_path=request.output_path,
        final_doc=final_doc,
    )

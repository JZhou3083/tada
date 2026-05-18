import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from tada.application.graph_runner import run_graph_with_status
from tada.application.ports import NullStatusSink, StatusSink
from tada.domain.sections import WorkbookSection
from tada.domain.workbook import Workbook
from tada.graph.workbook_documenter.graph import build_documentation_workflow

logger = logging.getLogger(__name__)


# TODO: consider moving to pydantic model for built-in validation
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
    sink = status_sink or NullStatusSink()

    # Pre-process the workbook using our pre-existing XML -> JSON parsing approach
    logger.debug("Parsing workbook: %s", request.workbook_path)
    workbook = Workbook.from_file(request.workbook_path)
    logger.debug("Parsed workbook.")

    if run_config.debug and run_config.artifacts_dir:
        run_config.artifacts_dir.mkdir(parents=True, exist_ok=True)
        workbook.write_debug(run_config.artifacts_dir)
        logger.debug("Wrote debug artifacts to %s", run_config.artifacts_dir)

    if run_config.checkpoints_path:
        checkpointer = SqliteSaver(sqlite3.connect(run_config.checkpoints_path))
        workflow = build_documentation_workflow(checkpointer=checkpointer)
    else:
        workflow = build_documentation_workflow()

    logger.debug(
        "Invoking documentation graph...",
    )

    final_state = run_graph_with_status(
        graph=workflow,
        input_state={
            "workbook": workbook,
            "generation_plan": request.sections,
            "run_summary_step": request.run_summary_step,
        },
        status_sink=sink,
    )

    final_doc = final_state["final_doc"]

    logger.debug("Graph complete.")

    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    request.output_path.write_text(final_doc, encoding="utf-8")

    return DocumentWorkbookResult(
        output_path=request.output_path,
        final_doc=final_doc,
    )

import logging
from dataclasses import dataclass
from pathlib import Path

from tada.application.graph_runner import run_graph_with_status
from tada.application.ports import NullStatusSink, StatusSink
from tada.cli.config import cli_config
from tada.domain.sections import WorkbookSection
from tada.domain.workbook import Workbook
from tada.graph.workbook_documenter.graph import build_documentation_workflow


from tada.observability.langfuse_client import get_langfuse
from tada.observability.reporter import finalise_observability

from langfuse import observe, propagate_attributes

langfuse = get_langfuse()

logger = logging.getLogger(__name__)


# TODO: consider moving to pydantic model for built-in validation
@dataclass(frozen=True)
class DocumentWorkbookRequest:
    workbook_path: Path
    output_path: Path
    sections: list[WorkbookSection]
    run_summary_step: bool = True
    all_sections: AllSectionsOpt = False


@dataclass(frozen=True)
class DocumentWorkbookResult:
    output_path: Path
    final_doc: str


def document_workbook(
    request: DocumentWorkbookRequest,
    *,
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
    workbook_name = getattr(workbook, "name", None) or Path(request.workbook_path).stem
    section_hint = 'ALL' if request.all_sections else "-".join(section[0].upper() for section in request.sections)

    logger.debug("Parsed workbook.")

    if cli_config.debug:
        workbook.write_debug(cli_config.debug_dir)
        logger.debug("Wrote parsed workbook contents to %s", cli_config.debug_dir)

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

    finalise_observability(run_id='TaDA')

    return DocumentWorkbookResult(
        output_path=request.output_path,
        final_doc=final_doc,
    )

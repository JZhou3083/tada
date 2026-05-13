import logging
from dataclasses import dataclass
from pathlib import Path

from rich.live import Live

from tada.cli.config import cli_config
from tada.cli.display.console import console
from tada.cli.display.graph_status import (
    GraphStatusDisplay,
)
from tada.cli.options import AllSectionsOpt
from tada.domain.sections import WorkbookSection
from tada.domain.workbook import Workbook
from tada.graph.events import GraphStatusEvent, GraphStatusStore
from tada.graph.workbook_documenter.graph import build_documentation_workflow
from tada.graph.workbook_documenter.state import InputState


from tada.observability.langfuse_client import get_langfuse
from tada.observability.reporter import finalise_observability

from langfuse import observe, propagate_attributes

langfuse = get_langfuse()

logger = logging.getLogger(__name__)


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

@observe(name="documentation_workflow")
def document_workbook(request: DocumentWorkbookRequest) -> DocumentWorkbookResult:
    """Generate Markdown documentation for a Tableau workbook.

    This function resolves invokes the documentation workflow, and writes the generated
    documentation to disk.
    """

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
    workflow_input = InputState(
        workbook=workbook,
        generation_plan=request.sections,
        run_summary_step=request.run_summary_step,
    )

    logger.debug(
        "Invoking documentation graph...",
    )

    statuses = GraphStatusStore()
    display = GraphStatusDisplay(total_sections=len(request.sections))

    # TODO: all live concerns should ultimately be fed back to the CLI to display, consider adding a progress handler to the func
    with Live(
        display.build(statuses),
        refresh_per_second=10,
        console=console,
    ) as live:

        def refresh():
            live.update(display.build(statuses))

        with propagate_attributes(
                metadata={
                    "workflow": "documentation",
                    "version": "v1",
                    "section.count": str(len(request.sections)),
                    "workbook": workbook_name,
                    "sections": section_hint,
                    "env": "dev"
                }
            ):
            documentation = None

            for chunk in workflow.stream(
                input=workflow_input,
                stream_mode=["custom", "values"],
                subgraphs=True,
                version="v2",
            ):
                if chunk["type"] == "custom":
                    status_update: GraphStatusEvent = chunk["data"]
                    statuses.apply(status_update)

                    refresh()

                elif chunk["type"] == "values":
                    documentation: str | None = chunk["data"].get("final_doc")

    logger.debug("Graph complete.")

    if not documentation:
        raise ValueError("Expected key `final_doc` not found in graph output")

    request.output_path.write_text(documentation, encoding="utf-8")

    console.print(
        f"[green]✔[/green] Documentation exported → {request.output_path.name}"
    )

    finalise_observability(run_id='TaDA')

    return DocumentWorkbookResult(
        output_path=request.output_path,
        final_doc=documentation,
    )

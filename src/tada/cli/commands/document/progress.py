from rich.live import Live

from tada.application.document_workbook import (
    DocumentWorkbookRequest,
    DocumentWorkbookRunConfig,
    document_workbook,
)
from tada.cli.display.console import console
from tada.cli.display.documentation_progress import (
    DocumentationProgressDisplay,
    RichDocumentationProgressSink,
)
from tada.graph.events import GraphStatusStore


def run_document_with_progress(
    request: DocumentWorkbookRequest,
    run_config: DocumentWorkbookRunConfig,
):
    status_store = GraphStatusStore.from_sections(
        [s.value for s in request.sections] + ["summary"]
    )
    display = DocumentationProgressDisplay(total_sections=len(status_store.sections))

    with Live(
        display.render(status_store), console=console, refresh_per_second=8
    ) as live:
        sink = RichDocumentationProgressSink(
            display=display, store=status_store, live=live
        )
        result = document_workbook(
            request,
            run_config=run_config,
            status_sink=sink,
        )

    console.print(f"[green]Documentation written to {result.output_path}[/green]")

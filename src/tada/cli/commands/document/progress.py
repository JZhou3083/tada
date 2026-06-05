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
from tada.graph.status import GraphStatusStore
from tada.observability.cost import CostSuccess


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

    llm_call_costs = [c.metadata.cost for c in result.llm_calls]
    total_cost = sum(
        c.total_cost_usd for c in llm_call_costs if isinstance(c, CostSuccess)
    )

    console.print(f"[green]Documentation written to {result.output_path}[/green]")
    console.print(f"[dim]Total cost: {total_cost}")

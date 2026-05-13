from __future__ import annotations

from rich.live import Live

from tada.application.ports import StatusSink
from tada.cli.display.documentation_progress import DocumentationProgressDisplay
from tada.graph.events import GraphStatusEvent, GraphStatusStore


class RichDocumentationProgressSink(StatusSink):
    """Applies graph status events and refreshes the Rich live display."""

    def __init__(
        self,
        *,
        display: DocumentationProgressDisplay,
        store: GraphStatusStore,
        live: Live,
    ) -> None:
        self.display = display
        self.store = store
        self.live = live

    def handle(self, event: GraphStatusEvent) -> None:
        self.store.apply(event)
        self.refresh()

    def refresh(self) -> None:
        self.live.update(self.display.render(self.store))

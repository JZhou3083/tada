from __future__ import annotations

from typing import Protocol

from tada.graph.events import GraphStatusEvent


class StatusSink(Protocol):
    def handle(self, event: GraphStatusEvent) -> None:
        """Receive graph status events."""
        ...


class NullStatusSink:
    def handle(self, event: GraphStatusEvent) -> None:
        pass

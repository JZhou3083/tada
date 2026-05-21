from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Mapping, Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import (
    SpanExporter,
    SpanExportResult,
)


class OpenInferenceJSONLSpanExporter(SpanExporter):
    """
    Writes one OpenTelemetry span per line as debuggable JSONL.

    Uses a readable span format that preserves OpenInference semantic-convention
    attributes exactly.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._file = self.path.open("a", encoding="utf-8")
        self._is_shutdown = False

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._is_shutdown:
            return SpanExportResult.FAILURE

        try:
            with self._lock:
                for span in spans:
                    self._file.write(
                        json.dumps(
                            self._serialise(span),
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                    )
                    self._file.write("\n")

                self._file.flush()

            return SpanExportResult.SUCCESS

        except Exception:
            return SpanExportResult.FAILURE

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        if self._is_shutdown:
            return True

        with self._lock:
            self._file.flush()

        return True

    def shutdown(self) -> None:
        if self._is_shutdown:
            return

        with self._lock:
            self._file.flush()
            self._file.close()
            self._is_shutdown = True

    @staticmethod
    def _serialise(span: ReadableSpan) -> dict[str, Any]:
        ctx = span.context
        parent = span.parent

        attributes = _json_safe_dict(span.attributes or {})
        resource = _json_safe_dict(span.resource.attributes or {})

        start_ns = span.start_time
        end_ns = span.end_time

        duration_ms = None
        if start_ns is not None and end_ns is not None:
            duration_ms = (end_ns - start_ns) / 1_000_000

        instrumentation_scope = getattr(span, "instrumentation_scope", None)

        return {
            "schema": "tada.openinference.span.v1",
            # Core trace identity
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
            "parent_id": format(parent.span_id, "016x") if parent else None,
            "trace_state": str(ctx.trace_state) if ctx.trace_state else None,
            # Span basics
            "name": span.name,
            "kind": span.kind.name if span.kind else None,
            "status": {
                "code": span.status.status_code.name,
                "description": span.status.description,
            },
            "start_ns": start_ns,
            "end_ns": end_ns,
            "duration_ms": duration_ms,
            # Debug-friendly OpenInference shortcuts
            "openinference_span_kind": attributes.get("openinference.span.kind"),
            "input": attributes.get("input.value"),
            "input_mime_type": attributes.get("input.mime_type"),
            "output": attributes.get("output.value"),
            "output_mime_type": attributes.get("output.mime_type"),
            "model": attributes.get("llm.model_name"),
            "token_count": {
                "prompt": attributes.get("llm.token_count.prompt"),
                "completion": attributes.get("llm.token_count.completion"),
                "total": attributes.get("llm.token_count.total"),
            },
            # Preserve canonical attributes exactly
            "attributes": attributes,
            # Span events
            "events": [
                {
                    "name": event.name,
                    "timestamp_ns": event.timestamp,
                    "attributes": _json_safe_dict(event.attributes or {}),
                }
                for event in span.events
            ],
            # Span links
            "links": [
                {
                    "trace_id": format(link.context.trace_id, "032x"),
                    "span_id": format(link.context.span_id, "016x"),
                    "trace_state": str(link.context.trace_state)
                    if link.context.trace_state
                    else None,
                    "attributes": _json_safe_dict(link.attributes or {}),
                }
                for link in span.links
            ],
            # Resource and instrumentation metadata
            "resource": resource,
            "instrumentation_scope": {
                "name": instrumentation_scope.name if instrumentation_scope else None,
                "version": instrumentation_scope.version
                if instrumentation_scope
                else None,
            },
            # Dropped counts can be useful when debugging missing payloads
            "dropped": {
                "attributes": span.dropped_attributes,
                "events": span.dropped_events,
                "links": span.dropped_links,
            },
        }


def _json_safe_dict(values: Mapping[str, Any]) -> dict[str, Any]:
    return {str(k): _json_safe(v) for k, v in values.items()}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}

    if isinstance(value, list | tuple):
        return [_json_safe(v) for v in value]

    return str(value)

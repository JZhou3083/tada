from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
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
        context = span.context
        parent = span.parent

        attributes = _json_safe_dict(span.attributes or {})

        # Prefer OpenInference span kind if present.
        # Phoenix UI is most useful when this is LLM, CHAIN, TOOL, RETRIEVER, etc.
        span_kind = (
            attributes.get("openinference.span.kind")
            or attributes.get("span.kind")
            or span.kind.name
        )

        span_data = {
            "schema": "tada.openinference.span.v1",
            "name": span.name,
            "span_kind": span_kind,
            "parent_id": _span_id_to_hex(parent.span_id) if parent else None,
            "start_time": _ns_to_datetime(span.start_time),
            "end_time": _ns_to_datetime(span.end_time),
            "status_code": span.status.status_code.name,
            "status_message": span.status.description,
            "context.span_id": _span_id_to_hex(getattr(context, "span_id")),
            "context.trace_id": _trace_id_to_hex(getattr(context, "trace_id")),
        }
        span_data.update(
            {
                f"attributes.{key}": _json_safe(value)
                for key, value in attributes.items()
            }
        )

        return span_data


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


def _ns_to_datetime(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(
        value / 1_000_000_000,
        tz=timezone.utc,
    ).isoformat()


def _span_id_to_hex(span_id: int | None) -> str | None:
    if not span_id:
        return None
    return format(span_id, "016x")


def _trace_id_to_hex(trace_id: int | None) -> str | None:
    if not trace_id:
        return None
    return format(trace_id, "032x")

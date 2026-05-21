from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


def _ns_to_datetime(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1_000_000_000, tz=timezone.utc)


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _json_safe_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    return {k: _json_safe(v) for k, v in value.items()}


def _iter_jsonl(path: str | Path) -> Iterable[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def jsonl_spans_to_dataframe(path: str | Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for span in _iter_jsonl(path):
        attributes = span.get("attributes") or {}
        resource = span.get("resource") or {}
        status = span.get("status") or {}

        span_kind = (
            span.get("openinference_span_kind")
            or attributes.get("openinference.span.kind")
            or attributes.get("span.kind")
            or span.get("kind")
        )

        row: dict[str, Any] = {
            "name": span.get("name"),
            "span_kind": span_kind,
            "parent_id": span.get("parent_id"),
            "start_time": _ns_to_datetime(span.get("start_ns")),
            "end_time": _ns_to_datetime(span.get("end_ns")),
            "status_code": status.get("code"),
            "status_message": status.get("description"),
            "context.span_id": span.get("span_id"),
            "context.trace_id": span.get("trace_id"),
        }

        # Flatten canonical attributes back into Phoenix-style columns.
        for key, value in attributes.items():
            row[f"attributes.{key}"] = _json_safe(value)

        # Flatten resource attributes.
        for key, value in resource.items():
            row[f"resource.{key}"] = _json_safe(value)

        # Optional: keep JSONL-only metadata for debugging.
        row["duration_ms"] = span.get("duration_ms")
        row["trace_state"] = span.get("trace_state")
        row["events"] = _json_safe(span.get("events") or [])
        row["links"] = _json_safe(span.get("links") or [])
        row["instrumentation_scope"] = _json_safe(
            span.get("instrumentation_scope") or {}
        )
        row["dropped"] = _json_safe(span.get("dropped") or {})

        rows.append(row)

    return pd.DataFrame(rows)

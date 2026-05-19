from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from opentelemetry.sdk.trace import ReadableSpan


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


def _span_id_to_hex(span_id: int | None) -> str | None:
    if not span_id:
        return None
    return format(span_id, "016x")


def _trace_id_to_hex(trace_id: int | None) -> str | None:
    if not trace_id:
        return None
    return format(trace_id, "032x")


def readable_spans_to_dataframe(
    spans: list[ReadableSpan],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for span in spans:
        context = span.get_span_context()
        parent = span.parent

        attributes = dict(span.attributes or {})

        # Prefer OpenInference span kind if present.
        # Phoenix UI is most useful when this is LLM, CHAIN, TOOL, RETRIEVER, etc.
        span_kind = (
            attributes.get("openinference.span.kind")
            or attributes.get("span.kind")
            or span.kind.name
        )

        row: dict[str, Any] = {
            "name": span.name,
            "span_kind": span_kind,
            "parent_id": _span_id_to_hex(parent.span_id) if parent else None,
            "start_time": _ns_to_datetime(span.start_time),
            "end_time": _ns_to_datetime(span.end_time),
            "status_code": span.status.status_code.name,
            "status_message": span.status.description,
            "context.span_id": _span_id_to_hex(context.span_id),
            "context.trace_id": _trace_id_to_hex(context.trace_id),
        }

        # Phoenix expects flattened attributes-style columns.
        for key, value in attributes.items():
            row[f"attributes.{key}"] = _json_safe(value)

        # Optional but useful for debugging.
        if span.resource:
            for key, value in span.resource.attributes.items():
                row[f"resource.{key}"] = _json_safe(value)

        rows.append(row)

    return pd.DataFrame(rows)

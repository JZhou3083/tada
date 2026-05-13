import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from opentelemetry.sdk.trace import ReadableSpan
from tada.observability.cost_calculator import calculate_cost
from tada.observability.langfuse_client import get_langfuse, get_span_exporter
from tada.observability.trace_printer import write_trace

import langfuse

langfuse = get_langfuse()

logger = logging.getLogger(__name__)

REPORT_DIR = Path("./reports")


# ======================
# Helpers
# ======================

def _duration_ms(span: ReadableSpan) -> float:
    if span.start_time and span.end_time:
        return round((span.end_time - span.start_time) / 1e6, 2)
    return 0.0


def _get_attr(span: ReadableSpan, key: str):
    val = (span.attributes or {}).get(key)
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return val
    return val


# ======================
# Span extraction
# ======================

SPAN_HEADERS = [
    "trace_id",
    "span_id",
    "name",
    "status",
    "section",
    "model",
    "duration_ms",
    "input_tokens",
    "output_tokens",
    "cache_tokens",
    "thought_tokens",
    "total_tokens",
    "cost_usd",
]


def extract_span_row(span: ReadableSpan) -> dict:
    usage = _get_attr(span, "langfuse.observation.usage_details") or {}
    model = _get_attr(span, "langfuse.observation.model.name") or "unknown"
    section = _get_attr(span, "langfuse.observation.metadata.section") or "unknown"
    cost = calculate_cost(model, usage) if model != "unknown" else {}

    return {
        "trace_id": format(span.context.trace_id, "032x") if span.context else "—",
        "span_id": format(span.context.span_id, "016x") if span.context else "—",
        "name": span.name,
        "status": span.status.status_code.name if span.status else "UNSET",
        "section": section,
        "model": model,
        "duration_ms": _duration_ms(span),
        "input_tokens": usage.get("prompt_token_count", 0),
        "output_tokens": usage.get("candidates_token_count", 0),
        "cache_tokens": usage.get("cached_content_token_count", 0),
        "thought_tokens": usage.get("thoughts_token_count", 0),
        "total_tokens": usage.get("total_token_count",0),
        "cost_usd": round(cost.get("total_cost_usd", 0.0), 6),
        #"cost_breakdown": cost.get("breakdown", {}),
    }


def get_trace_id(span: ReadableSpan) -> str:
    return format(span.context.trace_id, "032x")


def get_run_id(span: ReadableSpan) -> str:
    return get_trace_id(span)[:8]


# ======================
# Span CSV + logging
# ======================


def write_spans_csv(spans: Iterable[ReadableSpan], *, run_id: str) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    csv_path = REPORT_DIR / f"spans_TaDA_{timestamp}.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SPAN_HEADERS)
        writer.writeheader()

        for span in spans:
            if span.end_time is None:
                continue

            writer.writerow(extract_span_row(span))

    return csv_path


def log_span(span: ReadableSpan) -> None:
    row = extract_span_row(span)
    logger.debug(
        "SPAN | %-30s | %-12s | in=%7d out=%7d total=%7d | $%.6f",
        row["name"][:30],
        row["section"],
        #row["duration_ms"],
        row["input_tokens"],
        row["output_tokens"],
        row["total_tokens"],
        row["cost_usd"],
    )


# ======================
# Trace summary 
# ======================

TRACE_HEADERS = [
    "trace_id",
    "span_count",
    "errors",
    "total_ms",
    "input_tokens",
    "output_tokens",
    "cache_tokens",
    "thought_tokens",
    "total_tokens",
    "total_cost_usd",
]


def write_trace_summary(spans: Iterable[ReadableSpan], *, run_id: str) -> Path:
    rows = [extract_span_row(s) for s in spans]

    summary = {
        "trace_id": run_id,
        "span_count": len(rows),
        "errors": sum(1 for r in rows if r["status"] == "ERROR"),
        "total_ms": round(sum(r["duration_ms"] for r in rows), 5),
        "input_tokens": sum(r["input_tokens"] for r in rows),
        "output_tokens": sum(r["output_tokens"] for r in rows),
        "cache_tokens": sum(r["cache_tokens"] for r in rows),
        "thought_tokens": sum(r["thought_tokens"] for r in rows),
        "total_tokens": sum(r["total_tokens"] for r in rows),
        "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 6),
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = REPORT_DIR / f"trace_TaDA_{timestamp}.csv"

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TRACE_HEADERS)
        writer.writeheader()
        writer.writerow(summary)

    logger.debug("TRACE SUMMARY | spans=%d | total_ms=%.2f | cost=$%.6f",
                 summary["span_count"],
                 summary["total_ms"],
                 summary["total_cost_usd"])

    return path


def finalise_observability(*, run_id: str | None = None) -> None:
    """
    Flush telemetry, collect spans, and generate all reports.

    Args:
        run_id: Optional fixed run identifier. If not provided,
                derived automatically from trace_id.
    """

    langfuse.flush()

    span_exporter = get_span_exporter()
    spans: list[ReadableSpan] = span_exporter.spans

    if not spans:
        return
    
    trace_id = format(spans[0].context.trace_id, "032x")
    
    if not trace_id:
        trace_id = run_id
    try:
        write_trace(spans=spans, run_id=trace_id)
    except Exception:
        pass

    write_spans_csv(spans, run_id=trace_id)
    write_trace_summary(spans, run_id=trace_id)

import json
from datetime import datetime, timezone
from pathlib import Path
from langfuse import Langfuse
from opentelemetry.sdk.trace import ReadableSpan
from google.genai import types

import logging

logger = logging.getLogger(__name__)

TRACE_DIR = Path("./reports")
CHAR_LIMIT = 500

def _truncate(value, limit: int = CHAR_LIMIT):
    """Recursively truncate leaf strings in any structure."""
    if isinstance(value, str):
        return value[:limit] + "..." if len(value) > limit else value
    if isinstance(value, dict):
        return {k: _truncate(v, limit) for k, v in value.items()}
    if isinstance(value, list):
        return [_truncate(i, limit) for i in value]
    return value

def _span_to_dict(span: ReadableSpan) -> dict:
    raw = json.loads(span.to_json())
    return _truncate(raw)

def write_trace(spans: list[ReadableSpan], run_id: str = None) -> Path:
    """
    Write all spans to a single JSON file, truncated to 500 chars per leaf string.
    Returns the path written to.
    """
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    if not spans:
        print("No spans to write.")
        return

    first_ctx = spans[0].context
    run_id = run_id or (format(first_ctx.trace_id, "032x")[:8] if first_ctx else "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    trace_path = TRACE_DIR / f"trace_TaDA_{timestamp}.json"
    
    output = {
        "run_id": run_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "span_count": len(spans),
        "spans": [_span_to_dict(s) for s in spans],
    }
    with open(trace_path, "w") as f:
        json.dump(output, f, indent=2)
        print(f" Trace written → {trace_path.resolve()}")
    return trace_path

def get_prop_attrs(attrs) -> dict:
    """
    Extracts required attributes from the propagated attributes on a workflow level
    """
    
    return {
            "workbook":attrs.get("langfuse.trace.metadata.workbook") or '',
            "section.count":attrs.get("langfuse.trace.metadata.section.count") or '',
            "sections":attrs.get("langfuse.trace.metadata.sections") or '',
            "env":attrs.get("langfuse.trace.metadata.env") or ''
    }

def update_generation(
        response: types.GenerateContentResponse,
        langfuse: Langfuse,
        metadata: dict
):
    """
    Updates the trace with generation parameters
    """
    langfuse.update_current_generation(
        model=response.model_version,
        metadata=metadata,
        usage_details=response.usage_metadata.model_dump(exclude_none=True),
    )


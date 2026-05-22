from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from tada.trace_viewer._optional import require_module

logger = logging.getLogger(__name__)


class TraceRetrievalError(RuntimeError):
    """Base error for trace retrieval failures."""


class RunsDirectoryNotFound(TraceRetrievalError):
    def __init__(self, runs_path: Path):
        super().__init__(f"Runs folder not found: {runs_path}")
        self.runs_path = runs_path


class NoTraceFilesFound(TraceRetrievalError):
    def __init__(self, pattern: str):
        super().__init__(f"No trace files found for pattern: {pattern}")
        self.pattern = pattern


class NoReadableTracesFound(TraceRetrievalError):
    def __init__(self, skipped: list[SkippedTraceFile]):
        super().__init__("Trace files were discovered but none were readable.")
        self.skipped = skipped


@dataclass(frozen=True)
class TraceFileInfo:
    run_id: str
    path: Path
    size_bytes: int


class SkipReason(str, Enum):
    EMPTY_FILE = "empty_file"
    READ_ERROR = "read_error"
    NO_ROWS = "no_rows"


@dataclass(frozen=True)
class SkippedTraceFile:
    path: Path
    reason: SkipReason
    detail: str = ""


@dataclass(frozen=True)
class TraceLoadResult:
    traces: Any
    loaded_files: list[TraceFileInfo]
    skipped_files: list[SkippedTraceFile]


def discover_trace_files(
    runs_path: Path,
    *,
    pattern: str = "*/traces.jsonl",
) -> list[TraceFileInfo]:
    runs_path = runs_path.expanduser().resolve()

    if not runs_path.exists():
        raise RunsDirectoryNotFound(runs_path)

    files = sorted(
        runs_path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True
    )

    if not files:
        raise NoTraceFilesFound(pattern)

    return [
        TraceFileInfo(
            run_id=path.parent.name,
            path=path,
            size_bytes=path.stat().st_size,
        )
        for path in files
    ]


def load_traces(
    trace_files: Iterable[TraceFileInfo],
    *,
    max_files: int | None = None,
    include_columns: list[str] | None = None,
) -> TraceLoadResult:
    pd = require_module("pandas")

    loaded_frames: list[Any] = []
    loaded_files: list[TraceFileInfo] = []
    skipped_files: list[SkippedTraceFile] = []

    selected_files = list(trace_files)
    if max_files is not None:
        selected_files = selected_files[:max_files]

    for trace_file in selected_files:
        if trace_file.size_bytes == 0:
            skipped_files.append(
                SkippedTraceFile(trace_file.path, SkipReason.EMPTY_FILE)
            )
            continue

        try:
            frame = jsonl_spans_to_dataframe(trace_file.path)
        except Exception as exc:
            skipped_files.append(
                SkippedTraceFile(
                    trace_file.path,
                    SkipReason.READ_ERROR,
                    str(exc),
                )
            )
            continue

        if frame.empty:
            skipped_files.append(SkippedTraceFile(trace_file.path, SkipReason.NO_ROWS))
            continue

        frame.insert(0, "run_id", trace_file.run_id)
        frame.insert(1, "trace_file", str(trace_file.path))

        if include_columns:
            available = [col for col in include_columns if col in frame.columns]
            metadata = ["run_id", "trace_file"]
            frame = frame[[*metadata, *available]]

        loaded_frames.append(frame)
        loaded_files.append(trace_file)

    if not loaded_frames:
        raise NoReadableTracesFound(skipped_files)

    return TraceLoadResult(
        traces=pd.concat(loaded_frames, ignore_index=True),
        loaded_files=loaded_files,
        skipped_files=skipped_files,
    )


def jsonl_spans_to_dataframe(path: str | Path) -> Any:
    pd = require_module("pandas")
    return pd.read_json(path, lines=True)

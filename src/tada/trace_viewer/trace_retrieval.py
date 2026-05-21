from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ------------------------
# Domain errors
# ------------------------


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
    def __init__(self, skipped: list["SkippedTraceFile"]):
        super().__init__("Trace files were discovered but none were readable.")
        self.skipped = skipped


# ------------------------
# Structured results
# ------------------------


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
    traces: pd.DataFrame
    loaded_files: list[TraceFileInfo]
    skipped_files: list[SkippedTraceFile]


# ------------------------
# Trace APIs
# ------------------------


def discover_trace_files(
    runs_path: Path,
    *,
    pattern: str = "*/traces.jsonl",
) -> list[TraceFileInfo]:
    """
    Discover trace jsonl files under runs_path.

    Returns TraceFileInfo entries sorted by path.
    Raises:
      - RunsDirectoryNotFound
      - NoTraceFilesFound
    """
    if not runs_path.exists():
        raise RunsDirectoryNotFound(runs_path)

    paths = sorted(runs_path.glob(pattern))
    if not paths:
        raise NoTraceFilesFound(f"{runs_path}/{pattern}")

    infos: list[TraceFileInfo] = []
    for p in paths:
        try:
            size = p.stat().st_size
        except OSError as exc:
            # treat unreadable stat as skip at load stage; still include discovery
            logger.warning("Failed to stat trace file %s: %s", p, exc)
            size = -1

        infos.append(TraceFileInfo(run_id=p.parent.name, path=p, size_bytes=size))

    return infos


def load_traces(
    trace_files: Iterable[TraceFileInfo],
    *,
    max_files: Optional[int] = None,
    include_columns: Optional[list[str]] = None,
) -> TraceLoadResult:
    """
    Load traces from parquet files into a single DataFrame.

    - Skips empty files
    - Skips unreadable parquet files
    - Skips frames with no rows
    - Adds tada_run_id and tada_trace_file columns

    Raises:
      - NoReadableTracesFound (if nothing could be loaded)
    """
    loaded: list[TraceFileInfo] = []
    skipped: list[SkippedTraceFile] = []
    frames: list[pd.DataFrame] = []

    for i, info in enumerate(trace_files):
        if max_files is not None and i >= max_files:
            break

        # empty file defense
        if info.size_bytes == 0:
            skipped.append(
                SkippedTraceFile(info.path, SkipReason.EMPTY_FILE, "0 bytes")
            )
            continue

        try:
            df = pd.read_parquet(info.path, columns=include_columns)
        except Exception as exc:
            skipped.append(
                SkippedTraceFile(
                    info.path,
                    SkipReason.READ_ERROR,
                    f"{type(exc).__name__}: {exc}",
                )
            )
            continue

        if df.empty:
            skipped.append(
                SkippedTraceFile(info.path, SkipReason.NO_ROWS, "empty frame")
            )
            continue

        df = df.copy()
        df["tada_run_id"] = info.run_id
        df["tada_trace_file"] = str(info.path)

        frames.append(df)
        loaded.append(info)

    if not frames:
        raise NoReadableTracesFound(skipped)

    traces_df = pd.concat(frames, ignore_index=True)

    return TraceLoadResult(
        traces=traces_df,
        loaded_files=loaded,
        skipped_files=skipped,
    )

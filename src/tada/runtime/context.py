from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

RUNS_DIR = "runs"

RUN_METADATA_FILE = "run.json"
LOGS_FILE = "app.log"
TRACES_FILE = "traces.jsonl"
CHECKPOINTS_FILE = "checkpoints.db"
ARTIFACTS_DIR = "artifacts"


@dataclass(frozen=True)
class RunInfo:
    """Identifiers and timestamps associated with a run."""

    run_id: str
    started_at: datetime
    run_dir: Path


@dataclass(frozen=True)
class RunPaths:
    """Filesystem paths for data produced during a run."""

    metadata_path: Path
    logs_path: Path
    traces_path: Path
    checkpoints_path: Path
    artifacts_dir: Path


@dataclass(frozen=True)
class RunContext:
    """
    Per-invocation context describing run identity and filesystem layout.

    A ``RunContext`` provides a unique identifier for the run and the
    canonical paths where run-related data may be written, including logs,
    traces, checkpoints, metadata, and generated artefacts.
    """

    info: RunInfo
    """Run identity information such as ID, start time, and base directory."""

    paths: RunPaths
    """Filesystem locations associated with the run."""

    @classmethod
    def create(cls, *, state_dir: Path) -> Self:
        """
        Create a new run context under the given state directory.

        Generates a run identifier, initialises the run directory, and
        computes paths for run artefacts.

        Args:
            state_dir: Base directory where runs are stored.

        Returns:
            A new ``RunContext`` instance.
        """
        started_at = datetime.now(UTC)
        timestamp = started_at.strftime("%Y-%m-%dT%H-%M-%SZ")
        run_id = f"{timestamp}_{uuid.uuid4().hex[:6]}"
        run_dir = state_dir / RUNS_DIR / run_id

        run_dir.mkdir(parents=True, exist_ok=False)

        info = RunInfo(
            run_id=run_id,
            started_at=started_at,
            run_dir=run_dir,
        )

        paths = RunPaths(
            metadata_path=run_dir / RUN_METADATA_FILE,
            logs_path=run_dir / LOGS_FILE,
            traces_path=run_dir / TRACES_FILE,
            checkpoints_path=run_dir / CHECKPOINTS_FILE,
            artifacts_dir=run_dir / ARTIFACTS_DIR,
        )

        return cls(info=info, paths=paths)

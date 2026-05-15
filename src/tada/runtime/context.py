from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

RUNS_DIR = "runs"

RUN_METADATA_FILE = "run.json"
TRACES_FILE = "traces.jsonl"
CHECKPOINTS_FILE = "checkpoints.db"

type JSONValue = (
    str | int | float | bool | None | list[JSONValue] | dict[str, JSONValue]
)


@dataclass(frozen=True)
class TadaRunContext:
    """
    Immutable, per-invocation execution context.

    A RunContext describes *where* all artefacts for a single run should live
    (traces, checkpoints, metadata) and provides a stable identifier for correlating
    observability, debugging output, and filesystem state.

    It contains no business logic and owns no resources. Creation and shutdown
    of runtime resources (OTEL providers, files, checkpointers) are handled
    separately by the TadaRuntime.
    """

    run_id: str
    run_dir: Path
    metadata_path: Path
    traces_path: Path
    checkpoints_path: Path
    started_at: datetime

    @classmethod
    def create(cls, *, state_dir: Path) -> Self:
        """
        Create a new run context under the given TaDA state directory.

        This eagerly creates the run directory and checkpoint directory but
        does not open files or initialise observability.
        """
        started_at = datetime.now(UTC)
        run_id = started_at.strftime("%Y-%m-%dT%H-%M-%SZ")

        run_dir = state_dir / RUNS_DIR / run_id

        ctx = cls(
            run_id=run_id,
            run_dir=run_dir,
            metadata_path=run_dir / RUN_METADATA_FILE,
            traces_path=run_dir / TRACES_FILE,
            checkpoints_path=run_dir / CHECKPOINTS_FILE,
            started_at=started_at,
        )

        ctx._write_metadata(completed=False)

        return ctx

    def mark_completed(self) -> None:
        """Mark the run as completed in metadata."""
        self._write_metadata(
            completed=True,
            ended_at=datetime.now(UTC).isoformat(),
        )

    def mark_failed(self, error: BaseException) -> None:
        """Mark the run as failed in metadata."""
        self._write_metadata(
            completed=False,
            failed=True,
            ended_at=datetime.now(UTC).isoformat(),
            error_type=type(error).__name__,
            error_message=str(error),
        )

    def _write_metadata(self, **extra: JSONValue) -> None:
        data = {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "run_dir": str(self.run_dir),
            "traces_path": str(self.traces_path),
            "checkpoints_path": str(self.checkpoints_path),
            **extra,
        }

        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

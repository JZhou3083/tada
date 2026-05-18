import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self, TextIO

from opentelemetry import trace as otel_trace
from opentelemetry.instrumentation.langchain import LangchainInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

from tada.runtime.context import TadaRunContext


class RunStateStore:
    """Persist run lifecycle metadata to disk."""

    def __init__(self, context: TadaRunContext) -> None:
        self._context = context

    # ------------------------
    # Lifecycle methods
    # ------------------------

    def mark_started(self) -> None:
        """Record the start of a run."""
        self._write_metadata(
            status="running",
            started_at=self._context.info.started_at.isoformat(),
        )

    def mark_completed(self) -> None:
        """Record successful completion of a run."""
        self._write_metadata(
            status="completed",
            completed=True,
            ended_at=datetime.now(UTC).isoformat(),
        )

    def mark_failed(self, exc: Exception) -> None:
        """Record failure of a run and associated error details."""
        self._write_metadata(
            status="failed",
            completed=False,
            failed=True,
            ended_at=datetime.now(UTC).isoformat(),
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

    # ------------------------
    # Internal helpers
    # ------------------------

    def _write_metadata(self, **extra: Any) -> None:
        """Write run metadata to disk, merging with existing content if present."""
        path = self._context.paths.metadata_path

        base = {
            "run_id": self._context.info.run_id,
            "run_dir": str(self._context.info.run_dir),
            "started_at": self._context.info.started_at.isoformat(),
            "traces_path": str(self._context.paths.traces_path),
            "checkpoints_path": str(self._context.paths.checkpoints_path),
        }

        existing = self._load_existing(path)

        data = {
            **existing,
            **base,
            **extra,
        }

        path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    def _load_existing(self, path: Path) -> dict[str, Any]:
        """Load existing metadata if present."""
        if not path.exists():
            return {}

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}


class AppRuntime:
    """
    Runtime container for a single CLI invocation.

    Owns lifecycle-managed infrastructure such as OpenTelemetry,
    file-backed exporters, and run-level services.

    Use as a context manager to ensure proper setup and teardown.
    """

    def __init__(self, *, context: TadaRunContext) -> None:
        self.context = context

        self.trace_file: TextIO | None = None
        self.tracer_provider: TracerProvider | None = None

        self.run_state = RunStateStore(context)

        self._is_shutdown = False

        self._configure_environment()

    def _configure_environment(self) -> None:
        # Tell Langfuse SDK not to create its own exporter/transport.
        os.environ.setdefault("LANGFUSE_SECRET_KEY", "local")
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "local")
        os.environ.setdefault("LANGFUSE_HOST", "http://localhost:0")
        os.environ["OTEL_SDK_DISABLED"] = "false"

    def _setup_tracing(self) -> None:
        self.trace_file = open(
            self.context.paths.traces_path,
            "a",
            encoding="utf-8",
        )

        self.tracer_provider = TracerProvider()
        self.tracer_provider.add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter(out=self.trace_file))
        )

        # Set the provider globally BEFORE langfuse imports.
        otel_trace.set_tracer_provider(self.tracer_provider)

        LangchainInstrumentor().instrument()

    def __enter__(self) -> Self:
        self._setup_tracing()
        self.run_state.mark_started()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc:
                self.run_state.mark_failed(exc)
            else:
                self.run_state.mark_completed()
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        if self._is_shutdown:
            return

        try:
            if self.tracer_provider:
                self.tracer_provider.shutdown()
        finally:
            if self.trace_file:
                self.trace_file.close()
            self._is_shutdown = True

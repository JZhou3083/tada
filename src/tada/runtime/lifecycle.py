import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from tada.observability.otel.jsonl_exporter import OpenInferenceJSONLSpanExporter
from tada.runtime.context import RunContext


class RunStateStore:
    """Persist run lifecycle metadata to disk."""

    def __init__(self, context: RunContext) -> None:
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


class TadaRuntime:
    """
    Runtime container for a single TaDA CLI invocation.

    Owns lifecycle-managed infrastructure such as OpenTelemetry, file-backed exporters,
    and run-level services.

    Use as a context manager to ensure proper setup and teardown.
    """

    def __init__(self, *, context: RunContext) -> None:
        self.context = context
        self.run_state = RunStateStore(context)

        self.tracer_provider: TracerProvider | None = None
        self.span_processor: BatchSpanProcessor | None = None
        self.span_exporter: OpenInferenceJSONLSpanExporter | None = None

        self._is_shutdown = False
        self._is_instrumented = False

    def _setup_tracing(self) -> None:
        """
        Configure tracing with a local JSONL export.
        """
        resource = Resource.create(
            {
                "service.name": "tada-cli",
                "service.instance.id": str(self.context.info.run_id),
                "deployment.environment": "local",
                "tada.run_id": str(self.context.info.run_id),
            }
        )

        self.tracer_provider = TracerProvider(resource=resource)

        self.span_exporter = OpenInferenceJSONLSpanExporter(
            path=self.context.paths.traces_path
        )

        self.span_processor = BatchSpanProcessor(
            self.span_exporter,
            # Low overhead defaults for CLI/local use.
            max_queue_size=512,
            max_export_batch_size=128,
            schedule_delay_millis=2_000,
            export_timeout_millis=3_000,
        )

        self.tracer_provider.add_span_processor(self.span_processor)
        trace.set_tracer_provider(self.tracer_provider)

        GoogleGenAIInstrumentor().instrument(tracer_provider=self.tracer_provider)
        self._is_instrumented = True

    def __enter__(self) -> Self:
        self._setup_tracing()
        self.run_state.mark_started()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            if exc:
                self.run_state.mark_failed(exc)
            else:
                self.run_state.mark_completed()
        finally:
            self.shutdown()

        return False  # Returning False makes it explicit that errors are not suppressed

    def shutdown(self) -> None:
        """
        Flush and shutdown telemetry cleanly.

        Important for CLI apps because the process may exit before
        BatchSpanProcessor has exported queued spans.
        """
        if self._is_shutdown:
            return

        try:
            if self._is_instrumented:
                GoogleGenAIInstrumentor().uninstrument()
                self._is_instrumented = False

            if self.tracer_provider:
                self.tracer_provider.force_flush(timeout_millis=5_000)
                self.tracer_provider.shutdown()

        finally:
            self._is_shutdown = True

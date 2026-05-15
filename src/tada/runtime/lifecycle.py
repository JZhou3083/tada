import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Self, TextIO

from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

from tada.runtime.context import TadaRunContext


class TadaRuntime:
    """
    Process-level runtime registry for run-scoped infrastructure.

    This class owns long-lived runtime resources created for a single CLI run,
    such as OpenTelemetry providers and file-backed exporters.

    It centralises setup and teardown for resources that need to live for the
    duration of a run and be flushed or closed during process shutdown.

    Typical usage:
    ```
    with TadaRuntime(context=context):
        # Execute command logic for this run.
        ...
    # On exit, the tracer provider is shut down and the trace file is closed.
    ```

    Responsibilities:
    - Store the run context for the current invocation.
    - Configure process-level observability, including OpenTelemetry.
    - Own file-backed exporters and related runtime resources.
    - Provide a single, safe place to flush and close resources.

    Notes:
    - OpenTelemetry's tracer provider is process-global, so this runtime should
    generally be created once per process/CLI invocation.
    - `shutdown()` is idempotent and may be called manually, but using the context
    manager form is preferred.
    """

    def __init__(self, *, context: TadaRunContext) -> None:
        self.run_context = context
        self.trace_file: TextIO = open(
            self.run_context.traces_path,
            "a",
            encoding="utf-8",
        )

        self.tracer_provider = TracerProvider()
        self.tracer_provider.add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter(out=self.trace_file))
        )

        self._is_shutdown = False

        self._configure_environment()
        self._configure_otel()

    def _configure_environment(self) -> None:
        # Tell Langfuse SDK not to create its own exporter/transport.
        os.environ.setdefault("LANGFUSE_SECRET_KEY", "local")
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "local")
        os.environ.setdefault("LANGFUSE_HOST", "http://localhost:0")
        os.environ["OTEL_SDK_DISABLED"] = "false"

    def _configure_otel(self) -> None:
        # Set the provider globally BEFORE langfuse imports.
        otel_trace.set_tracer_provider(self.tracer_provider)

    def shutdown(self) -> None:
        if self._is_shutdown:
            return

        try:
            self.tracer_provider.shutdown()
        finally:
            self.trace_file.close()
            self._is_shutdown = True

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.shutdown()

    @classmethod
    @contextmanager
    def run(cls, *, context: TadaRunContext) -> Iterator[Self]:
        runtime = cls(context=context)
        try:
            yield runtime
        finally:
            runtime.shutdown()

from __future__ import annotations

import logging
from typing import Any

import structlog
from rich.console import Console
from rich.text import Text

from tada.cli.state import TadaCliOptions
from tada.runtime.context import TadaRunContext

# ---------------------------------------------------------------------------
# Structlog processors
# ---------------------------------------------------------------------------


def _add_otel_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add active OpenTelemetry trace context to the log event, if available.

    This processor intentionally has no hard dependency on OpenTelemetry.
    If OTel is not installed, or if no span is currently recording, the event
    is returned unchanged.
    """
    try:
        from opentelemetry import trace  # noqa: PLC0415
    except ImportError:
        return event_dict

    span = trace.get_current_span()

    if not span.is_recording():
        return event_dict

    span_context = span.get_span_context()
    event_dict["trace_id"] = format(span_context.trace_id, "032x")
    event_dict["span_id"] = format(span_context.span_id, "016x")

    return event_dict


# ---------------------------------------------------------------------------
# Rich console handler
# ---------------------------------------------------------------------------


class RichConsoleLogHandler(logging.Handler):
    """
    A standard logging handler that routes formatted log strings
    through an existing, shared Rich Console instance.
    """

    def __init__(self, console: Console):
        super().__init__()
        self.console = console

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Get the fully processed string from structlog's Formatter
            msg = self.format(record)
            # Convert structlog's ANSI color codes into a Rich Text object
            rich_text = Text.from_ansi(msg)
            # Print via the singleton console (handles live status/progress safely!)
            self.console.print(rich_text)
        except Exception:
            self.handleError(record)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def configure_logging(
    console: Console,
    run_context: TadaRunContext,
    cli_options: TadaCliOptions,
):
    """Configure logging for one TaDA CLI invocation.

    This function is safe to call multiple times. Existing handlers are removed
    before new handlers are attached, preventing duplicate log output in tests
    or repeated CLI setup.
    """

    _shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,  # picks up bind_contextvars() context
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_otel_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Configure the File Handler (Always JSON)
    log_file = run_context.paths.logs_path
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        # Processors to run on standard library logs BEFORE JSON rendering
        foreign_pre_chain=_shared_processors,
        # The final renderer for the file
        processor=structlog.processors.JSONRenderer(),
    )
    file_handler.setFormatter(file_formatter)

    # Configure the Console Handler (Dynamic based on debug flag)
    console_handler = RichConsoleLogHandler(console)
    console_handler.setLevel(logging.DEBUG if cli_options.debug else logging.WARNING)
    console_renderer = structlog.dev.ConsoleRenderer(
        colors=True,
    )
    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_shared_processors,
        processor=console_renderer,
    )
    console_handler.setFormatter(console_formatter)

    # Configure the Standard Library Root Logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # NOTE: currently the code below suppresses any logs from third-party libraries
    # unless they are >=WARNING, this is to avoid too much noise in logs which is rarely
    # useful.
    root_logger.setLevel(logging.WARNING)

    # Set the app logger specifically to allow debug - this will cascade to any loggers
    # retrieved using __name__ e.g. tada.llm.gateway
    app_logger = logging.getLogger("tada")
    app_logger.setLevel(logging.DEBUG if cli_options.debug else logging.INFO)

    # 6. Finalize Structlog configuration
    structlog.configure(
        processors=_shared_processors
        + [
            # Prepares data to be shipped off to the standard library handlers
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

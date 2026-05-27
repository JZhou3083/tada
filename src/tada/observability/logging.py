from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import structlog
from rich.console import Console
from rich.logging import RichHandler
from rich.markup import escape

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


_SHARED_PROCESSORS: list[Any] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
    _add_otel_context,
    # Must be last: hands the event dictionary to ProcessorFormatter.
    structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
]


# ---------------------------------------------------------------------------
# Rich console rendering
# ---------------------------------------------------------------------------


_LEVEL_STYLES: dict[str, tuple[str, str]] = {
    "debug": ("DEBUG", "dim"),
    "info": ("INFO", "bold cyan"),
    "warning": ("WARNING", "bold yellow"),
    "error": ("ERROR", "bold red"),
    "critical": ("CRITICAL", "bold red reverse"),
}

_INTERNAL_KEYS = frozenset(
    {
        "_record",
        "_from_structlog",
        "logger",
        "stack_info",
        "exc_info",
    }
)


def _rich_renderer(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> str:
    """Render a structlog event as Rich markup for terminal output."""

    level = str(event_dict.pop("level", "info")).lower()
    event = str(event_dict.pop("event", ""))
    timestamp = str(event_dict.pop("timestamp", ""))

    for key in _INTERNAL_KEYS:
        event_dict.pop(key, None)

    label, style = _LEVEL_STYLES.get(level, ("INFO", "bold"))

    parts = [
        f"[dim]{escape(timestamp)}[/dim]",
        f"[{style}]{label:<8}[/{style}]",
        f"[white]{escape(event)}[/white]",
    ]

    if event_dict:
        fields = "  ".join(
            f"[dim]{escape(str(key))}[/dim]=[cyan]{escape(str(value))}[/cyan]"
            for key, value in event_dict.items()
        )
        parts.append(fields)

    return "  ".join(parts)


class _RichStructlogHandler(logging.Handler):
    """Logging handler that prints structlog-rendered Rich markup."""

    def __init__(self, console: Console) -> None:
        super().__init__()
        self._console = console

    def emit(self, record: logging.LogRecord) -> None:
        """Format and print a log record using Rich markup."""
        try:
            message = self.format(record)
            self._console.print(message, markup=True, highlight=False)
        except Exception:  # noqa: BLE001
            self.handleError(record)


# ---------------------------------------------------------------------------
# Handler factories
# ---------------------------------------------------------------------------


def _make_console_handler(console: Console, debug: bool) -> _RichStructlogHandler:
    """Create the Rich console handler for TaDA application logs."""

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            _rich_renderer,
        ],
    )

    handler = _RichStructlogHandler(console)
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG if debug else logging.WARNING)

    return handler


def _make_file_handler(log_path: Path) -> logging.FileHandler:
    """Create the JSON file handler for TaDA application logs."""

    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)

    return handler


def _make_root_handler(console: Console, debug: bool) -> RichHandler:
    """Create the root handler used for third-party stdlib logs."""

    return RichHandler(
        console=console,
        show_time=False,
        show_path=debug,
        rich_tracebacks=True,
        tracebacks_show_locals=debug,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def configure_logging(
    *,
    console: Console,
    run_context: TadaRunContext,
    cli_options: TadaCliOptions,
) -> None:
    """Configure logging for one TaDA CLI invocation.

    This function is safe to call multiple times. Existing handlers are removed
    before new handlers are attached, preventing duplicate log output in tests
    or repeated CLI setup.
    """

    structlog.configure(
        processors=_SHARED_PROCESSORS,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    tada_logger = logging.getLogger("tada")
    tada_logger.handlers.clear()
    tada_logger.setLevel(logging.DEBUG)
    tada_logger.propagate = False

    tada_logger.addHandler(_make_console_handler(console, cli_options.debug))
    tada_logger.addHandler(_make_file_handler(run_context.paths.logs_path))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)
    root_logger.addHandler(_make_root_handler(console, cli_options.debug))

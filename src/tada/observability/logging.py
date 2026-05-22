import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from tada.cli.state import TadaCliOptions
from tada.runtime.context import TadaRunContext


class TaDALogFilter(logging.Filter):
    """Allow full verbosity for TaDA logs while throttling third-party noise.

    This filter passes all records from loggers under the ``tada`` namespace
    (any level, including DEBUG). For all other loggers, it only allows
    WARNING and above to reduce verbose output from dependencies.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # TaDA logs: allow everything (DEBUG+)
        if record.name.startswith("tada"):
            return True
        # Logs from other libraries: WARNING+
        return record.levelno >= logging.WARNING


def _create_file_formatter() -> logging.Formatter:
    return logging.Formatter("%(asctime)s  %(name)-40s  %(levelname)-8s  %(message)s")


def configure_logging(
    *,
    console: Console,
    run_context: TadaRunContext,
    cli_options: TadaCliOptions,
) -> None:
    """Configure Python logging for a CLI invocation."""

    handlers: list[logging.Handler] = []

    # ------------------------
    # Console handler
    # ------------------------

    console_handler = RichHandler(
        console=console,
        show_time=cli_options.debug,
        show_path=cli_options.debug,
        rich_tracebacks=True,
        tracebacks_show_locals=cli_options.debug,
    )

    console_handler.setLevel(logging.DEBUG if cli_options.debug else logging.WARNING)
    console_handler.addFilter(TaDALogFilter())

    handlers.append(console_handler)

    # ------------------------
    # File handler (always on)
    # ------------------------

    log_path: Path = run_context.paths.logs_path

    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_create_file_formatter())
    file_handler.addFilter(TaDALogFilter())

    handlers.append(file_handler)

    # TODO: add an OpenTel handler so logs appear in traces?

    # ------------------------
    # Root config
    # ------------------------

    logging.basicConfig(
        level=logging.DEBUG if cli_options.debug else logging.INFO,
        handlers=handlers,
        force=True,
    )

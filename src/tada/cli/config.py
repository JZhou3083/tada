import logging
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from rich.console import Console
from rich.logging import RichHandler

_DEBUG_ROOT = Path(".tada_debug")
_GITIGNORE_CONTENT = "*\n!.gitignore\n"


def _default_debug_dir() -> Path:
    # TODO: when shipping as a tool, it'd be best to move debug dir to Path.home() / ".tada"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return _DEBUG_ROOT / timestamp


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


class CLIConfig(BaseModel):
    model_config = ConfigDict(
        frozen=False  # mutable - debug is set after init in callback / commands
    )

    debug: bool = False
    debug_dir: Path = Field(default_factory=_default_debug_dir)

    def apply_debug(self, command_level: bool) -> None:
        """Merge command-level --debug flag with any globally set flag."""
        self.debug = self.debug or command_level

    def ensure_debug_dir(self) -> Path:
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        gitignore = _DEBUG_ROOT / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(_GITIGNORE_CONTENT)
        return self.debug_dir

    def configure_logging(self, console: Console) -> None:
        handlers: list[logging.Handler] = []

        # Rich console handler - pretty & minimal for use in non-debug mode
        console_handler = RichHandler(
            console=console,
            show_time=self.debug,
            show_path=self.debug,
            rich_tracebacks=True,
            tracebacks_show_locals=self.debug,
        )
        console_handler.setLevel(logging.DEBUG if self.debug else logging.WARNING)
        console_handler.addFilter(TaDALogFilter())
        handlers.append(console_handler)

        # File handler - only in debug mode, full verbosity
        if self.debug:
            log_file = self.ensure_debug_dir() / "debug.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s  %(name)-40s  %(levelname)-8s  %(message)s"
                )
            )
            file_handler.addFilter(TaDALogFilter())
            handlers.append(file_handler)

        logging.basicConfig(
            level=logging.DEBUG if self.debug else logging.WARNING,
            handlers=handlers,
            force=True,  # override any library config that ran before this
        )


cli_config = CLIConfig()

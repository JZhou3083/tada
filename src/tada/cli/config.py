from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


def _default_debug_dir() -> Path:
    # TODO: when shipping as a tool, it'd be best to move debug dir to Path.home() / ".tada"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return Path(".tada-debug") / timestamp


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
        return self.debug_dir


cli_config = CLIConfig()

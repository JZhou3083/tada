from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

import typer


class RegisterFunction(Protocol):
    def __call__(self, app: typer.Typer) -> None:
        """Register a command to the Typer app."""
        ...


InteractiveRunFunction = Callable[[typer.Context], Any]


@dataclass(frozen=True)
class AppCommand:
    """Metadata and handlers for a CLI command.

    Attributes:
        name: Command name shown in the CLI and interactive menu.
        interactive_menu_desc: Short description shown in the interactive menu.
        register: Function that registers the command with the Typer app.
        run: Function executed when the command is selected from the interactive menu.
            It receives the active Typer context so it can access shared runtime state.
    """

    name: str
    interactive_menu_desc: str
    register: RegisterFunction
    run: InteractiveRunFunction

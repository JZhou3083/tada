from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

import typer


class RegisterFunction(Protocol):
    def __call__(self, app: typer.Typer) -> None:
        """Register a command to the Typer app."""
        ...


@dataclass(frozen=True)
class AppCommand:
    name: str
    interactive_menu_desc: str
    register: RegisterFunction
    run: Callable[..., Any]

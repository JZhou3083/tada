from __future__ import annotations

from importlib import import_module
from types import ModuleType


class OptionalDependencyError(RuntimeError):
    """Raised when an optional trace viewer dependency is missing."""


def require_module(module_name: str) -> ModuleType:
    try:
        return import_module(module_name)
    except ImportError as exc:
        raise OptionalDependencyError(
            "This feature requires optional dependencies.\n\n"
            "Install them with: pip install 'tada[trace-viewer]'"
        ) from exc

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Callable, Sequence

import typer


def make_suffix_validator(
    allowed: Sequence[str] | str,
    *,
    param_hint: str,
) -> Callable[[Path | None], Path | None]:
    """
    Create a Typer option callback that validates a Path's file suffix.

    Args:
        allowed: Allowed suffix(es), e.g. ".md" or (".twb", ".twbx").
        param_hint: Passed to typer.BadParameter to show which option failed.

    Returns:
        A callback(value) that returns the Path (or None) or raises BadParameter.
    """
    if isinstance(allowed, str):
        allowed_suffixes = (allowed,)
    else:
        allowed_suffixes = tuple(allowed)

    display = ", ".join(repr(s) for s in allowed_suffixes)

    def callback(value: Path | None) -> Path | None:
        if value is None:
            return None

        if value.suffix not in allowed_suffixes:
            raise typer.BadParameter(
                f"File '{value.name}' must have extension {display}",
                param_hint=param_hint,
            )
        return value

    return callback


validate_workbook_option = make_suffix_validator(
    (".twb", ".twbx"),
    param_hint="--workbook",
)

validate_markdown_option = make_suffix_validator(
    ".md",
    param_hint="--output",
)


WorkbookOpt = Annotated[
    Path | None,
    typer.Option(
        "--workbook",
        "-w",
        callback=validate_workbook_option,
        help="Path to a Tableau workbook. If omitted, you will be prompted to select one.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
]


OutputOpt = Annotated[
    Path | None,
    typer.Option(
        "--output",
        "-o",
        callback=validate_markdown_option,
        help="Path to save final markdown docs. If omitted, you will be prompted to select one.",
        exists=False,
        file_okay=True,
        dir_okay=False,
        writable=True,
    ),
]

DebugOpt = Annotated[
    bool,
    typer.Option(
        "--debug",
        help="Enable debug mode: print logs to the terminal and save logs and intermediate JSON to .tada_debug/.",
    ),
]

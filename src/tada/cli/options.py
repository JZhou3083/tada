from pathlib import Path
from typing import Annotated

import typer


def validate_workbook_option(value: Path | None) -> Path | None:
    """
    Validate that an optional file path refers to a Tableau workbook (.twb or .twbx).

    This function is intended for use as a Typer option callback. If a path
    is provided and does not have a ``.twb`` or ```.twbx``` suffix, a
    ``typer.BadParameter`` error is raised to signal invalid CLI input.

    Args:
        value: Optional path supplied via the ``--file`` option.

    Returns:
        The original path if valid, or ``None`` if no path was provided.

    Raises:
        typer.BadParameter: If the path does not point to a ``.twb`` or ```.twbx``` file.
    """
    if value and value.suffix not in (".twb", ".twbx"):
        raise typer.BadParameter(
            f"File '{value.name}' is not a Tableau workbook ('.twb' or '.twbx')",
            param_hint="--workbook",
        )
    return value


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

DebugOpt = Annotated[
    bool,
    typer.Option(
        "--debug",
        help="Enable debug mode: print logs to the terminal and save logs and intermediate JSON to .tada_debug/.",
    ),
]

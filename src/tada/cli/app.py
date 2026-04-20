import json
import time
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from tada.cli.prompts import ask_workbook_file
from tada.graph.builder import State, graph

app = typer.Typer(
    name="Tableau Documentation Agent",
    no_args_is_help=True,
    help="CLI interface for the Tableau Documentation Agent.",
    add_completion=True,
)
console = Console()


def validate_workbook_option(value: Path | None) -> Path | None:
    """
    Validate that an optional file path refers to a Tableau workbook (.twb).

    This function is intended for use as a Typer option callback. If a path
    is provided and does not have a ``.twb`` suffix, a ``typer.BadParameter``
    error is raised to signal invalid CLI input.

    Args:
        value: Optional path supplied via the ``--file`` option.

    Returns:
        The original path if valid, or ``None`` if no path was provided.

    Raises:
        typer.BadParameter: If the path does not point to a ``.twb`` file.
    """
    if value and value.suffix != ".twb":
        raise typer.BadParameter(
            f"File '{value.name}' is not a Tableau workbook (.twb)",
            param_hint="--workboook",
        )
    return value


WorkbookOpt = Annotated[
    Path | None,
    typer.Option(
        "--workbook",
        "-w",
        callback=validate_workbook_option,
        help="Path to a Tableau workbook (.twb). If omitted, you will be prompted to select one.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
]


@app.command(
    name="document",
    help="Document a Tableau workbook using a standardized workflow.",
)
def document_workbook(
    workbook: WorkbookOpt = None,
) -> None:
    """
    Generate documentation for a Tableau workbook.

    If no workbook is provided via the CLI, you will be prompted to interactively select
    a Tableau workbook (.twb). The command then processes the workbook and produces
    documentation output.
    """

    # Prompt users to select a workbook if one wasn't provided as a CLI argument
    if not workbook:
        workbook = ask_workbook_file("Select a Tableau workbook (.twb)")

    # Pre-process the workbook using our pre-existing XML -> JSON parsing approach
    # TODO: convert this from a mockup to actual functional pre-processing
    with console.status("Processing workbook...", spinner="dots"):
        time.sleep(1)

    # TODO: convert this from a mockup to actually generating documentation
    with console.status("Generating documentation...", spinner="dots"):
        time.sleep(2)

        graph_input = State(query=f"process workbook '{workbook.name}'")
        result = graph.invoke(graph_input)

    console.print("[green]✔[/green] Generated response:")
    console.print_json(json=json.dumps(result))

    # TODO: determine actual export logic
    console.print("[green]✔[/green] Documentation exported → ???")


@app.command(
    name="compare",
    help="Review differences between two or more Tableau workbooks.",
)
def compare_workbooks():
    # TODO: create comparison logic or delete command
    console.print(
        "[yellow]Command not yet available.[/yellow] "
        "Workbook comparison is still under development."
    )
    raise typer.Exit(0)


@app.command(
    name="chat",
    help="Ask questions about a Tableau workbook in a free-form conversation.",
)
def chat_with_workbooks():
    # TODO: create chat logic or delete command
    console.print(
        "[yellow]Command not yet available.[/yellow] "
        "Chat features are still under development."
    )
    raise typer.Exit(0)


def main():
    app()

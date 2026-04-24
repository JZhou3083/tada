import typer
from rich.console import Console

from tada.cli.commands._base import AppCommand

console = Console()


def run_compare() -> None:
    # TODO: create comparison logic or delete command
    console.print(
        "[yellow]Command not yet available.[/yellow] "
        "Workbook comparison is still under development."
    )
    raise typer.Exit(0)


def register(app: typer.Typer) -> None:
    @app.command(
        name="compare",
        help="Review differences between two or more Tableau workbooks.",
    )
    def cmd_compare() -> None:
        run_compare()


COMMAND = AppCommand(
    name="compare",
    interactive_menu_desc="Compare multiple workbooks",
    register=register,
    run=run_compare,
)

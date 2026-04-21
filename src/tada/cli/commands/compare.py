import typer
from rich.console import Console

console = Console()


def register(app: typer.Typer) -> None:
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

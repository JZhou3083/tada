import typer
from rich.console import Console

console = Console()


def register(app: typer.Typer) -> None:
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

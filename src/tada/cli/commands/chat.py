import typer
from rich.console import Console

from tada.cli.commands._base import AppCommand
from tada.cli.display import print_tada_banner

console = Console()


def run_chat() -> None:
    # TODO: create chat logic or delete command
    console.print(
        "[yellow]Command not yet available.[/yellow] "
        "Chat features are still under development."
    )
    raise typer.Exit(0)


def register(app: typer.Typer) -> None:
    @app.command(
        name="chat",
        help="Ask questions about a Tableau workbook in a free-form conversation.",
    )
    def cmd_chat():
        print_tada_banner(console, subtitle="Workbook QA")
        run_chat()


COMMAND = AppCommand(
    name="chat",
    interactive_menu_desc="Ask free-form questions about a workbook",
    register=register,
    run=run_chat,
)

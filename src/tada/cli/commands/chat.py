import typer

from tada.cli.commands._base import AppCommand
from tada.cli.config import cli_config
from tada.cli.display import console, print_tada_banner
from tada.cli.options import DebugOpt


def run_chat() -> None:
    # TODO: create chat logic or delete command
    console.print(
        "[yellow]Command not yet available.[/yellow] "
        "Chat features are still under development."
    )
    raise typer.Exit(0)


def _cmd_chat(debug: DebugOpt = False):
    cli_config.apply_debug(debug)
    print_tada_banner(console, subtitle="Workbook QA")
    run_chat()


def register(app: typer.Typer) -> None:
    app.command(
        name="chat",
        help="Ask questions about a Tableau workbook in a free-form conversation.",
    )(_cmd_chat)


COMMAND = AppCommand(
    name="chat",
    interactive_menu_desc="Ask free-form questions about a workbook",
    register=register,
    run=run_chat,
)

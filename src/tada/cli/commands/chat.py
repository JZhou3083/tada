import typer

from tada.cli.commands.base import AppCommand
from tada.cli.config import cli_config
from tada.cli.display.banners import (
    print_debug_notice_banner,
    print_tada_banner,
)
from tada.cli.display.console import console
from tada.cli.state import TadaCliState, get_cli_state


def run_chat(cli_state: TadaCliState) -> None:
    """Run the workbook chat workflow.

    Args:
        cli_state: CLI state for the current TaDA execution.
    """
    # TODO: create chat logic or delete command
    console.print(
        "[yellow]Command not yet available.[/yellow] "
        "Chat features are still under development."
    )
    raise typer.Exit(0)


def handle_chat(
    ctx: typer.Context,
) -> None:
    """Handle execution of the chat command from any CLI route.

    This function contains the shared command orchestration used by both direct
    command invocation and the interactive menu.
    Args:
        ctx: Typer context containing the current TaDA CLI state.
    """
    cli_state = get_cli_state(ctx)
    run_chat(cli_state=cli_state)


def _cmd_chat(ctx: typer.Context):
    """CLI entrypoint for the ``chat`` command.

    Args:
        ctx: Typer context containing the current TaDA CLI state.
    """
    print_tada_banner(console, subtitle="Workbook QA")
    if cli_config.debug:
        print_debug_notice_banner(console, debug_dir=cli_config.debug_dir)

    handle_chat(ctx)


def register(app: typer.Typer) -> None:
    """Register the ``chat`` command with the Typer app.

    Args:
        app: Typer application to register the command with.
    """
    app.command(
        name="chat",
        help="Ask questions about a Tableau workbook in a free-form conversation.",
    )(_cmd_chat)


COMMAND = AppCommand(
    name="chat",
    interactive_menu_desc="Ask free-form questions about a workbook",
    register=register,
    run=handle_chat,
)

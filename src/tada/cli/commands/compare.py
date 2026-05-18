import typer

from tada.cli.commands.base import AppCommand
from tada.cli.config import cli_config
from tada.cli.context import get_run_context
from tada.cli.display.banners import (
    print_debug_notice_banner,
    print_tada_banner,
)
from tada.cli.display.console import console
from tada.runtime.context import TadaRunContext


def run_compare(run_context: TadaRunContext) -> None:
    """Run the workbook comparison workflow.

    Args:
        run_context: Runtime context for the current TaDA execution.
    """
    # TODO: create comparison logic or delete command
    console.print(
        "[yellow]Command not yet available.[/yellow] "
        "Workbook comparison is still under development."
    )
    raise typer.Exit(0)


def handle_compare(
    ctx: typer.Context,
) -> None:
    """Handle execution of the compare command from any CLI route.

    This function contains the shared command orchestration used by both direct
    command invocation and the interactive menu.
    Args:
        ctx: Typer context containing the current TaDA runtime context.
    """
    run_context = get_run_context(ctx)
    run_compare(run_context=run_context)


def _cmd_compare(ctx: typer.Context) -> None:
    """CLI entrypoint for the ``compare`` command.

    Args:
        ctx: Typer context containing the current TaDA runtime context.
    """
    cli_config.configure_logging(console)
    print_tada_banner(console=console, subtitle="Workbook comparison")
    if cli_config.debug:
        print_debug_notice_banner(console, debug_dir=cli_config.debug_dir)

    handle_compare(ctx)


def register(app: typer.Typer) -> None:
    """Register the ``compare`` command with the Typer app.

    Args:
        app: Typer application to register the command with.
    """
    app.command(
        name="compare",
        help="Review differences between two or more Tableau workbooks.",
    )(_cmd_compare)


COMMAND = AppCommand(
    name="compare",
    interactive_menu_desc="Compare multiple workbooks",
    register=register,
    run=handle_compare,
)

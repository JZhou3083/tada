import typer

from tada.cli.commands.base import AppCommand
from tada.cli.config import cli_config
from tada.cli.display.banners import (
    print_debug_notice_banner,
    print_tada_banner,
)
from tada.cli.display.console import console
from tada.cli.options import DebugOpt


def run_compare() -> None:
    # TODO: create comparison logic or delete command
    console.print(
        "[yellow]Command not yet available.[/yellow] "
        "Workbook comparison is still under development."
    )
    raise typer.Exit(0)


def _cmd_compare(debug: DebugOpt = False) -> None:
    cli_config.apply_debug(debug)
    cli_config.configure_logging(console)
    print_tada_banner(console=console, subtitle="Workbook comparison")
    if cli_config.debug:
        print_debug_notice_banner(console, debug_dir=cli_config.debug_dir)
    run_compare()


def register(app: typer.Typer) -> None:
    app.command(
        name="compare",
        help="Review differences between two or more Tableau workbooks.",
    )(_cmd_compare)


COMMAND = AppCommand(
    name="compare",
    interactive_menu_desc="Compare multiple workbooks",
    register=register,
    run=run_compare,
)

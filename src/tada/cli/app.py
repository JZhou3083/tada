import warnings

import typer

from tada.cli.commands.chat import COMMAND as CHAT_COMMAND
from tada.cli.commands.compare import COMMAND as COMPARE_COMMAND
from tada.cli.commands.document import COMMAND as DOCUMENT_COMMAND
from tada.cli.config import cli_config
from tada.cli.display.banners import (
    print_debug_notice_banner,
    print_tada_banner,
)
from tada.cli.display.console import console
from tada.cli.menu import prompt_for_command
from tada.cli.options import DebugOpt
from tada.config.settings import TadaSettings
from tada.runtime.context import TadaRunContext
from tada.runtime.lifecycle import TadaRuntime

# Silence this specific auth-warning which Google SDK prints directly to console
warnings.filterwarnings(
    "ignore",
    message=r".*authenticated using end user credentials from Google Cloud SDK without a quota project.*",
    category=UserWarning,
    module=r"google\.auth\._default",
)

app = typer.Typer(
    name="Tableau Documentation Agent (TaDA)",
    no_args_is_help=False,
    rich_markup_mode="rich",
    epilog=(
        "[bold cyan]Tip:[/bold cyan] Run [bold]tada[/bold] with no arguments to "
        "launch the interactive menu."
    ),
)


ALL_COMMANDS = [
    DOCUMENT_COMMAND,
    CHAT_COMMAND,
    COMPARE_COMMAND,
]


@app.callback(invoke_without_command=True)
def menu(
    ctx: typer.Context,
    debug: DebugOpt = False,
):
    """
    LLM-powered CLI tool for documenting and discussing Tableau workbooks.
    """
    # Apply debug status globally so subcommands can access it
    cli_config.apply_debug(debug)

    # If a subcommand was provided then proceed as normal
    if ctx.invoked_subcommand is not None:
        return

    # No subcommand -> route to the interactive launcher
    cli_config.configure_logging(console)
    print_tada_banner(
        console,
        subtitle="Interactive menu",
    )
    if cli_config.debug:
        print_debug_notice_banner(console, debug_dir=cli_config.debug_dir)

    prompt_for_command(ctx, ALL_COMMANDS)


def main():
    for cmd in ALL_COMMANDS:
        cmd.register(app)

    settings = TadaSettings()
    context = TadaRunContext.create(state_dir=settings.state_dir)

    # TODO: Define an app state object
    # TODO: Register callback inside main(), adding the state obj to typer ctx
    # TODO: Update all commands to pass context in

    with TadaRuntime(context=context):
        try:
            app()
        except Exception as exc:
            context.mark_failed(exc)
            raise
        else:
            context.mark_completed()

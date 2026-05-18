import warnings

import typer

from tada.cli.commands.base import AppCommand
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


ALL_COMMANDS: list[AppCommand] = [
    DOCUMENT_COMMAND,
    CHAT_COMMAND,
    COMPARE_COMMAND,
]


def handle_entrypoint(
    ctx: typer.Context,
    run_context: TadaRunContext,
    debug: bool,
) -> None:
    """Handle shared CLI setup and route empty invocations to the interactive menu.

    This function is called by the root Typer callback before command execution.
    It attaches the current run context to the Typer context so subcommands can
    access runtime state, applies global debug configuration, and decides whether
    to continue with a user-provided subcommand or fall back to the interactive
    command prompt.

    Args:
        ctx: Typer invocation context for the current CLI run.
        run_context: Runtime context for the current TaDA execution.
        debug: Whether debug mode should be enabled for this invocation.
    """
    ctx.obj = run_context

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


def create_entrypoint_callback(run_context: TadaRunContext):
    """Create the root Typer callback bound to the current run context.

    Typer callbacks can only receive CLI-compatible parameters directly. This
    factory closes over the current ``TadaRunContext`` so the callback can pass it
    into ``handle_entrypoint`` without exposing it as a CLI argument.

    Args:
        run_context: Runtime context to make available to all commands.

    Returns:
        A Typer-compatible callback function for the root application.
    """

    def entrypoint(
        ctx: typer.Context,
        debug: DebugOpt = False,
    ):
        """Root CLI callback executed before subcommands or interactive fallback.

        Args:
            ctx: Typer invocation context for the current CLI run.
            debug: Whether debug mode should be enabled for this invocation.
        """
        handle_entrypoint(
            ctx=ctx,
            run_context=run_context,
            debug=debug,
        )

    return entrypoint


def main():
    """Run the TaDA command-line application.

    This is the console-script entrypoint. It registers available commands,
    creates the runtime context, wires the root Typer callback, executes the app
    inside the TaDA runtime lifecycle, and records whether the run completed or
    failed.
    """
    for cmd in ALL_COMMANDS:
        cmd.register(app)

    settings = TadaSettings()
    run_context = TadaRunContext.create(state_dir=settings.state_dir)

    # TODO: Define an app state object
    # TODO: Update all commands to pass context in

    app.callback(invoke_without_command=True)(create_entrypoint_callback(run_context))

    with TadaRuntime(context=run_context):
        try:
            app()
        except Exception as exc:
            run_context.mark_failed(exc)
            raise
        else:
            run_context.mark_completed()

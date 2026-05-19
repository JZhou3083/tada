import warnings

import typer
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry import trace

from tada.cli.commands.base import AppCommand
from tada.cli.commands.document import COMMAND as DOCUMENT_COMMAND
from tada.cli.commands.view_traces import COMMAND as VIEW_TRACES_COMMAND
from tada.cli.display.banners import print_command_header
from tada.cli.display.console import console
from tada.cli.menu import prompt_for_command
from tada.cli.options import DebugOpt
from tada.cli.state import TadaCliOptions, TadaCliState
from tada.config.settings import settings
from tada.observability.logging import configure_logging
from tada.runtime.context import TadaRunContext
from tada.runtime.lifecycle import AppRuntime

# Silence this specific auth-warning which Google SDK prints directly to console
warnings.filterwarnings(
    "ignore",
    message=r".*authenticated using end user credentials from Google Cloud SDK without a quota project.*",
    category=UserWarning,
    module=r"google\.auth\._default",
)

tracer = trace.get_tracer(__name__)

ALL_COMMANDS: list[AppCommand] = [
    DOCUMENT_COMMAND,
    VIEW_TRACES_COMMAND,
]


def handle_entrypoint(
    ctx: typer.Context,
    run_context: TadaRunContext,
    debug: bool,
) -> None:
    """Handle shared CLI setup and route empty invocations to the interactive menu.

    This function is called by the root Typer callback before command execution.
    It creates the CLI invocation state, attaches it to the Typer context,
    configures logging once, and decides whether to continue with a provided
    subcommand or fall back to the interactive command prompt.

    Args:
        ctx: Typer invocation context for the current CLI run.
        run_context: Runtime context for the current TaDA execution.
        debug: Whether debug mode should be enabled for this invocation.
    """
    with tracer.start_as_current_span("cli.entrypoint") as span:
        span.set_attribute(
            SpanAttributes.OPENINFERENCE_SPAN_KIND,
            OpenInferenceSpanKindValues.CHAIN.value,
        )

        cli_options = TadaCliOptions(debug=debug)

        ctx.obj = TadaCliState(
            run_context=run_context,
            cli_options=cli_options,
        )

        configure_logging(
            console=console,
            run_context=run_context,
            cli_options=cli_options,
        )

    # If a subcommand was provided then proceed as normal
    if ctx.invoked_subcommand is not None:
        return

    with tracer.start_as_current_span("cli.interactive_menu") as span:
        span.set_attribute(
            SpanAttributes.OPENINFERENCE_SPAN_KIND,
            OpenInferenceSpanKindValues.CHAIN.value,
        )

        # No subcommand -> route to the interactive launcher
        print_command_header(
            ctx,
            console,
            subtitle="Interactive menu",
        )

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


def create_tada_app(run_context: TadaRunContext) -> typer.Typer:
    """Create and configure the TaDA Typer CLI application.

    This function constructs a fresh ``typer.Typer`` instance, registers all available
    commands (discovered via ALL_COMMANDS), and wires the root callback that initialises
    CLI state and handles interactive fallback.

    Args:
        run_context: Runtime context for the current TaDA execution. This is
            injected into the root callback and made available to all commands
            via ``TadaCliState``.

    Returns:
        A fully configured ``typer.Typer`` application ready to be invoked.
    """
    app = typer.Typer(
        name="Tableau Documentation Agent (TaDA)",
        no_args_is_help=False,
        rich_markup_mode="rich",
        epilog=(
            "[bold cyan]Tip:[/bold cyan] Run [bold]tada[/bold] with no arguments to "
            "launch the interactive menu."
        ),
    )

    for cmd in ALL_COMMANDS:
        cmd.register(app)

    app.callback(invoke_without_command=True)(create_entrypoint_callback(run_context))
    return app


def main():
    """Run the TaDA command-line application.

    This is the console-script entrypoint. It creates the runtime context,
    builds the CLI application, executes it inside the TaDA runtime lifecycle,
    and records whether the run completed or failed.
    """
    run_context = TadaRunContext.create(state_dir=settings.state_dir)

    app = create_tada_app(run_context=run_context)

    with AppRuntime(context=run_context):
        with tracer.start_as_current_span("cli.run") as root_span:
            root_span.set_attribute(
                SpanAttributes.OPENINFERENCE_SPAN_KIND,
                OpenInferenceSpanKindValues.AGENT.value,
            )

            app()

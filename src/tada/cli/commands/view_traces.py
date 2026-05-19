import time
from contextlib import ExitStack

import typer
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry import trace
from rich.panel import Panel

from tada.cli.commands.base import AppCommand
from tada.cli.display.banners import print_command_header
from tada.cli.display.console import console
from tada.cli.display.errors import print_typer_error
from tada.cli.state import TadaCliState, get_cli_state
from tada.config.settings import settings
from tada.observability.phoenix_launcher import (
    PhoenixImportError,
    PhoenixLaunchError,
    launch_phoenix,
)
from tada.observability.trace_retrieval import (
    NoReadableTracesFound,
    NoTraceFilesFound,
    RunsDirectoryNotFound,
    discover_trace_files,
    load_traces,
)
from tada.runtime.context import RUNS_DIR

tracer = trace.get_tracer(__name__)


def run_view_traces(cli_state: TadaCliState) -> None:
    """Launch the local Arize Phoenix trace viewer.

    Args:
        cli_state: CLI state for the current TaDA execution.
    """
    with tracer.start_as_current_span("command.view_traces") as document_span:
        document_span.set_attribute(
            SpanAttributes.OPENINFERENCE_SPAN_KIND,
            OpenInferenceSpanKindValues.CHAIN.value,
        )

        try:
            import phoenix as px
        except ImportError:
            print_typer_error(
                console,
                "Missing optional dependency\n\n"
                "The view-traces command requires the optional dependency "
                "[bold]view-traces[/bold].\n\n"
                "Install it with:\n"
                "[bold green]uv sync --extra view-traces[/bold green]\n"
                "or\n"
                "[bold green]pip install -e '.[view-traces]'[/bold green]",
            )
            raise typer.Exit(1)

        runs_path = settings.state_dir / RUNS_DIR
        try:
            files = discover_trace_files(runs_path)
            result = load_traces(files, max_files=100)
        except RunsDirectoryNotFound as e:
            print_typer_error(
                console, f"Runs folder not found: [dim]{e.runs_path}[/dim]"
            )
            raise typer.Exit(1)
        except NoTraceFilesFound as e:
            print_typer_error(
                console, f"No trace files found. Expected: [dim]{e.pattern}[/dim]"
            )
            raise typer.Exit(1)
        except NoReadableTracesFound as e:
            detail = "\n".join(
                f"- {s.path} ({s.reason.value}: {s.detail})" for s in e.skipped[:10]
            )
            print_typer_error(
                console, "No readable traces found.\n\nSkipped files:\n" + detail
            )
            raise typer.Exit(1)

        traces_df = result.traces

        try:
            with ExitStack() as stack:
                # Show spinner only during startup
                with console.status("[cyan]Starting Phoenix...[/cyan]", spinner="dots"):
                    phoenix = stack.enter_context(
                        launch_phoenix(traces_df, suppress_warnings=True)
                    )

                # Spinner is now gone; session is still alive (managed by ExitStack)
                console.print(
                    Panel.fit(
                        "[bold green]Trace viewer is running[/bold green]\n\n"
                        f"Loaded [bold]{len(traces_df):,}[/bold] trace rows.\n"
                        f"Open Phoenix here:\n"
                        f"[bold blue underline]{phoenix.url}[/bold blue underline]\n\n"
                        "[dim]Press Ctrl+C to stop the viewer.[/dim]",
                        border_style="green",
                    )
                )

                while True:
                    time.sleep(1)

        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down trace viewer...[/yellow]")
            raise typer.Exit(0)

        except PhoenixImportError as exc:
            print_typer_error(console, f"Phoenix not available\n\n{exc}")
            raise typer.Exit(1)

        except PhoenixLaunchError as exc:
            print_typer_error(console, f"Failed to launch trace viewer\n\n{exc}")
            raise typer.Exit(1)


def handle_view_traces(
    ctx: typer.Context,
) -> None:
    """Handle execution of the view-traces command from any CLI route.

    This function contains the shared command orchestration used by both direct
    command invocation and the interactive menu.
    Args:
        ctx: Typer context containing the current TaDA CLI state.
    """
    cli_state = get_cli_state(ctx)
    run_view_traces(cli_state=cli_state)


def _cmd_view_traces(ctx: typer.Context) -> None:
    """CLI entrypoint for the ``view-traces`` command.

    Args:
        ctx: Typer context containing the current TaDA CLI state.
    """
    print_command_header(ctx, console, subtitle="Trace viewer", hint=None)

    handle_view_traces(ctx)


def register(app: typer.Typer) -> None:
    """Register the ``view-traces`` command with the Typer app.

    Args:
        app: Typer application to register the command with.
    """
    app.command(
        name="view-traces",
        help="View the traces from previous runs in a local Arize Phoenix server.",
    )(_cmd_view_traces)


COMMAND = AppCommand(
    name="view-traces",
    interactive_menu_desc="Launch a local Arize Phoenix server to inspect previous runs",
    register=register,
    run=handle_view_traces,
)

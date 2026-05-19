import logging
import time
import warnings
from pathlib import Path

import pandas as pd
import typer
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry import trace
from rich.panel import Panel
from sqlalchemy.exc import SAWarning

from tada.cli.commands.base import AppCommand
from tada.cli.display.banners import print_command_header
from tada.cli.display.console import console
from tada.cli.state import TadaCliState, get_cli_state

tracer = trace.get_tracer(__name__)


def _silence_phoenix_noise() -> None:
    warnings.filterwarnings(
        "ignore",
        message=r".*Skipped unsupported reflection of expression-based index.*",
        category=SAWarning,
    )

    logging.getLogger("phoenix.server.app").setLevel(logging.ERROR)


def _print_typer_error(message: str) -> None:
    console.print(
        Panel(
            message,
            title="Error",
            title_align="left",
            border_style="red",
        )
    )


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

        runs_path = Path(".tada") / "runs"

        if not runs_path.exists():
            _print_typer_error(
                f"Runs folder not found. Expected to find runs at: [dim]{runs_path}[/dim]"
            )
            raise typer.Exit(1)

        trace_paths = sorted(runs_path.glob("*/traces.parquet"))

        if not trace_paths:
            _print_typer_error(
                f"No trace files found. Expected to find files matching: "
                f"[dim]{runs_path}/*/traces.parquet[/dim]"
            )
            raise typer.Exit(1)

        try:
            import phoenix as px
        except ImportError:
            _print_typer_error(
                "[bold red]Missing optional dependency[/bold red]\n\n"
                "The trace viewer requires the optional dependency "
                "[bold]trace-viewer[/bold].\n\n"
                "Install it with:\n"
                "[bold green]pip install tada[trace-viewer][/bold green]"
            )
            raise typer.Exit(1)

        session = None
        try:
            with console.status("[cyan]Loading traces...[/cyan]", spinner="dots"):
                trace_frames: list[pd.DataFrame] = []
                skipped_files: list[str] = []

                for trace_path in trace_paths:
                    # Defend against:
                    # ArrowInvalid: Could not open Parquet input source '<Buffer>':
                    # Parquet file size is 0 bytes
                    if trace_path.stat().st_size == 0:
                        skipped_files.append(f"{trace_path} (empty file)")
                        continue

                    try:
                        df = pd.read_parquet(trace_path)
                    except Exception as exc:
                        skipped_files.append(
                            f"{trace_path} ({type(exc).__name__}: {exc})"
                        )
                        continue

                    if df.empty:
                        skipped_files.append(f"{trace_path} (no rows)")
                        continue

                    df = df.copy()
                    df["tada_run_id"] = trace_path.parent.name
                    df["tada_trace_file"] = str(trace_path)

                    trace_frames.append(df)

                if not trace_frames:
                    detail = "\n".join(f"- {file}" for file in skipped_files[:10])

                    _print_typer_error(
                        "No readable traces found.\n\n"
                        "Trace files were discovered, but none contained readable trace rows."
                        + (f"\n\nSkipped files:\n{detail}" if detail else "")
                    )
                    raise typer.Exit(1)

                traces_df = pd.concat(trace_frames, ignore_index=True)

            with console.status("[cyan]Starting Phoenix...[/cyan]", spinner="dots"):
                _silence_phoenix_noise()

                trace_dataset = px.TraceDataset(traces_df)
                session = px.launch_app(trace=trace_dataset)

            console.print(
                Panel.fit(
                    "[bold green]Trace viewer is running[/bold green]\n\n"
                    f"Loaded [bold]{len(traces_df):,}[/bold] trace rows from "
                    f"[bold]{len(trace_frames):,}[/bold] run(s).\n\n"
                    f"Open Phoenix here:\n"
                    f"[bold blue underline]{session.url if session else ''}[/bold blue underline]\n\n"
                    "[dim]Press Ctrl+C to stop the viewer.[/dim]",
                    border_style="green",
                )
            )

            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down trace viewer...[/yellow]")
            raise typer.Exit(0)

        except Exception as exc:
            _print_typer_error(
                "[bold red]Failed to launch trace viewer[/bold red]\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            raise typer.Exit(1)

        finally:
            if session:
                session.end()


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

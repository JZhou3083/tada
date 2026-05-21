import time
from contextlib import ExitStack

import typer
from opentelemetry import trace
from rich.panel import Panel

from tada.cli.display.console import console
from tada.cli.display.errors import print_typer_error
from tada.config.settings import settings
from tada.runtime.context import RUNS_DIR
from tada.trace_viewer.phoenix_launcher import (
    PhoenixImportError,
    PhoenixLaunchError,
    launch_phoenix,
)
from tada.trace_viewer.trace_retrieval import (
    NoReadableTracesFound,
    NoTraceFilesFound,
    RunsDirectoryNotFound,
    discover_trace_files,
    load_traces,
)

tracer = trace.get_tracer(__name__)


def run_view_traces() -> None:
    """Launch the local Arize Phoenix trace viewer.

    Args:
        cli_state: CLI state for the current TaDA execution.
    """
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
        print_typer_error(console, f"Runs folder not found: [dim]{e.runs_path}[/dim]")
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

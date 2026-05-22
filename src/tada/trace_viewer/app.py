import time

import typer
from rich.console import Console
from rich.panel import Panel

from tada.cli.display.console import print_typer_error
from tada.runtime.context import RUNS_DIR
from tada.settings import settings
from tada.trace_viewer._optional import OptionalDependencyError
from tada.trace_viewer.phoenix_launcher import (
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

console = Console()
app = typer.Typer()


@app.callback(invoke_without_command=True)
def view_traces() -> None:
    """Launch the local Arize Phoenix trace viewer."""
    try:
        trace_files = discover_trace_files(settings.state_dir / RUNS_DIR)
        result = load_traces(trace_files)

        with launch_phoenix(result.traces) as phoenix:
            console.print(
                Panel.fit(
                    f"[green]Phoenix trace viewer is running[/green]\n\n"
                    f"URL: {phoenix.url or 'see Phoenix output'}\n"
                    f"Loaded files: {len(result.loaded_files)}\n"
                    f"Skipped files: {len(result.skipped_files)}\n\n"
                    f"Press Ctrl+C to stop.",
                    title="Trace Viewer",
                )
            )

            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped Phoenix trace viewer.[/yellow]")
    except (
        RunsDirectoryNotFound,
        NoTraceFilesFound,
        NoReadableTracesFound,
        OptionalDependencyError,
        PhoenixLaunchError,
    ) as exc:
        print_typer_error(console, str(exc))
        raise typer.Exit(code=1) from exc


def main() -> None:
    app()

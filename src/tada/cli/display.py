import logging
from pathlib import Path

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import (
    Progress,
)
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from tada.cli.theme import SECTION_STATE_STYLE
from tada.graph.events import GraphStatusStore, SectionState

logger = logging.getLogger(__name__)
console = Console()


def print_tada_banner(
    console: Console,
    *,
    subtitle: str | None = None,
    hint: str | None = "↑/↓ Navigate • Enter Select • Ctrl+C Exit",
) -> None:
    title = Text()
    title.append("TaDA", style="bold cyan")
    title.append("  Tableau Documentation Agent", style="bold")

    body = Text()
    body.append_text(title)

    if subtitle:
        subtitle_text = Text(subtitle, style="dim")
        body.append("\n")
        body.append_text(subtitle_text)

    if hint:
        hint_text = Text(hint, style="italic grey70")
        body.append("\n")
        body.append_text(hint_text)

    console.print(
        Panel(
            Align.left(body),
            border_style="cyan",
            padding=(1, 2),
        ),
    )


def print_debug_notice(console: Console, debug_dir: Path) -> None:
    body = Text()
    body.append("Debug mode active\n", style="bold yellow")
    body.append("Artifacts will be written to ", style="dim")
    body.append(str(debug_dir), style="cyan")

    console.print(
        Panel(
            body,
            border_style="yellow",
            padding=(0, 2),
        )
    )


def build_graph_status_display(statuses: GraphStatusStore, progress: Progress) -> Group:
    """Compose the live display: phase label + section table + progress bar."""
    items = []

    # By-Section Status
    grid = Table.grid(padding=(0, 1))
    grid.add_column()

    tbl = Table(show_header=True, header_style="bold blue", box=None, padding=(0, 2))
    tbl.add_column("Step")
    tbl.add_column("Status")
    tbl.add_column("Attempts", justify="right")

    for sec_name, sec_status in statuses.sections.items():
        icon, color = SECTION_STATE_STYLE[sec_status.state]
        tbl.add_row(
            sec_name,
            Text(f"{icon} {sec_status.state.name.title()}", style=color),
            str(sec_status.attempts) if sec_status.attempts > 0 else "-",
        )

    grid.add_row(tbl)
    grid.add_row(Text(""))
    grid.add_row(progress)

    items.append(grid)

    # Summary
    if statuses.summary:
        items.append(Text(""))

        summary_grid = Table.grid(padding=(0, 1))
        summary_grid.add_column()

        summary_grid.add_row(Text("Summary", style="bold"))

        if statuses.summary.state == SectionState.DONE:
            summary_grid.add_row(Text("✅ Summary generated", style="green"))
        else:
            # Present the spinner for any summary state which is not DONE or `None`
            summary_grid.add_row(
                Spinner(
                    "dots",
                    text="Generating final summary...",
                    style="cyan",
                )
            )

        items.append(summary_grid)

    return Group(*items)

    # # Warnings
    # warnings = collect_quality_warnings(sections)

    # if warnings:
    #     items.append(Text(""))
    #     items.append(build_warnings_panel(warnings))

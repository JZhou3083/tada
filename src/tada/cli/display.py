import logging
from pathlib import Path

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from tada.cli.theme import ISSUE_SEVERITY_STYLE, SECTION_STATE_STYLE
from tada.graph.events import (
    SECTION_COMPLETE_STATES,
    GraphStatusStore,
    IssueSeverity,
    SectionState,
    Status,
    StatusIssue,
)

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


class GraphStatusDisplay:
    def __init__(self, total_sections: int) -> None:
        self.sections_progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} sections"),
            TimeElapsedColumn(),
        )
        self.overall = self.sections_progress.add_task(
            "Documenting sections",
            total=total_sections,
        )

    def build(self, statuses: GraphStatusStore) -> Group:
        self._sync_progress(statuses)

        items = [
            Rule("Sections", style="bold blue"),
            self._build_sections_table(statuses),
            Text(""),
            self.sections_progress,
        ]

        # sections_grid = Table.grid()
        # sections_grid.add_column()
        # sections_grid.add_row(Text("Sections", style="bold"))

        # sections_grid.add_row(self._build_sections_table(statuses))
        # sections_grid.add_row(Text(""))
        # sections_grid.add_row(self.sections_progress)

        # items.append(sections_grid)

        issues_table = self._build_issues_table(statuses)
        if issues_table is not None:
            items.extend(
                [
                    Text(""),
                    Rule("Issues", style="bold yellow"),
                    issues_table,
                ]
            )

            # issues_grid = Table.grid(padding=(0, 0))
            # issues_grid.add_column()

            # issues_grid.add_row(Text("Issues", style="bold"))
            # issues_grid.add_row(issues_table)

            # items.append(Padding(issues_grid, (1, 0, 0, 0)))

        # if statuses.summary:
        #     items.append(Text(""))
        #     items.append(self._build_summary(statuses.summary))

        if statuses.summary:
            items.extend(
                [
                    Text(""),
                    Rule("Summary", style="bold green"),
                    self._build_summary(statuses.summary),
                ]
            )

        return Group(*items)

    def _build_sections_table(self, statuses: GraphStatusStore) -> Table:
        tbl = Table(
            show_header=True,
            header_style="bold blue",
            box=None,
            padding=(0, 1),
        )
        tbl.add_column("Step", no_wrap=True, width=14)
        tbl.add_column("", no_wrap=True, width=3)
        tbl.add_column("Status", no_wrap=True, width=24)
        tbl.add_column("Attempts", no_wrap=True, width=8)
        tbl.add_column("Issues", no_wrap=True, width=12)

        for sec_name, sec_status in statuses.sections.items():
            icon, color = SECTION_STATE_STYLE[sec_status.state]

            tbl.add_row(
                sec_name,
                Text(icon, style=color, no_wrap=True),
                Text(
                    sec_status.state.name.replace("_", " ").title(),
                    style=color,
                    no_wrap=True,
                ),
                str(sec_status.attempts) if sec_status.attempts > 0 else "-",
                self._format_issue_count(sec_status),
            )

        return tbl

    def _build_issues_table(self, statuses: GraphStatusStore) -> Table | None:
        issue_rows = self._collect_issue_rows(statuses)

        if not issue_rows:
            return None

        table = Table(
            show_header=True,
            header_style="bold yellow",
            box=None,
            padding=(0, 1),
        )

        table.add_column("Step", no_wrap=True, width=14)
        table.add_column("Severity", no_wrap=True, width=9)
        table.add_column("Code", no_wrap=True, width=24, overflow="ellipsis")
        table.add_column("Issue", ratio=1, overflow="fold")

        for step_name, issue in issue_rows:
            style = ISSUE_SEVERITY_STYLE[issue.severity]

            table.add_row(
                step_name,
                Text(issue.severity.value.title(), style=style, no_wrap=True),
                issue.code or "-",
                issue.message,
            )

        return table

    def _build_summary(self, summary_status: Status) -> Table:
        summary_grid = Table.grid(padding=(0, 1))
        summary_grid.add_column()

        if summary_status.state in SECTION_COMPLETE_STATES:
            summary_grid.add_row(Text("✅ Summary generated", style="green"))
        else:
            summary_grid.add_row(
                Spinner(
                    "dots",
                    text="Generating final summary...",
                    style="cyan",
                )
            )

        return summary_grid

    def _collect_issue_rows(
        self,
        statuses: GraphStatusStore,
    ) -> list[tuple[str, StatusIssue]]:
        rows: list[tuple[str, StatusIssue]] = []

        section_order = {
            section_name: index
            for index, section_name in enumerate(statuses.sections.keys())
        }

        for section_name, section_status in statuses.sections.items():
            # Only want to surface error details for completed sections
            if section_status.state not in SECTION_COMPLETE_STATES:
                continue

            for issue in section_status.issues:
                rows.append((section_name, issue))

        # Only want to surface error details for summary if completed
        if statuses.summary and statuses.summary.state in SECTION_COMPLETE_STATES:
            for issue in statuses.summary.issues:
                rows.append(("summary", issue))

        return sorted(
            rows,
            key=lambda row: self._issue_sort_key(
                section_name=row[0],
                issue=row[1],
                section_order=section_order,
            ),
        )

    def _issue_sort_key(
        self,
        section_name: str,
        issue: StatusIssue,
        section_order: dict[str, int],
    ) -> tuple[int, int, str, str]:
        severity_order = {
            IssueSeverity.ERROR: 0,
            IssueSeverity.WARNING: 1,
            IssueSeverity.INFO: 2,
        }

        return (
            severity_order.get(issue.severity, 99),
            section_order.get(section_name, 999),
            issue.code or "",
            issue.message,
        )

    def _format_issue_count(self, status: Status) -> Text:
        if not status.issues:
            return Text("-")

        counts = {
            IssueSeverity.ERROR: 0,
            IssueSeverity.WARNING: 0,
            IssueSeverity.INFO: 0,
        }

        for issue in status.issues:
            if issue.severity in counts:
                counts[issue.severity] += 1

        parts: list[Text] = []

        if counts[IssueSeverity.ERROR]:
            parts.append(Text(f"E:{counts[IssueSeverity.ERROR]}", style="red"))
        if counts[IssueSeverity.WARNING]:
            parts.append(Text(f"W:{counts[IssueSeverity.WARNING]}", style="yellow"))
        if counts[IssueSeverity.INFO]:
            parts.append(Text(f"I:{counts[IssueSeverity.INFO]}", style="blue"))

        result = Text(no_wrap=True)
        for idx, part in enumerate(parts):
            if idx > 0:
                result.append(" ")
            result.append(part)

        return result

    def _sync_progress(self, statuses: GraphStatusStore) -> None:
        completed_sections = sum(
            1
            for status in statuses.sections.values()
            if status.state in (SectionState.DONE, SectionState.REACHED_RETRY_LIMIT)
        )

        self.sections_progress.update(
            self.overall,
            completed=completed_sections,
        )

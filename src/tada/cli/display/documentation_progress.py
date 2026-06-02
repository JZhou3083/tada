from __future__ import annotations

from collections import Counter

from rich.console import Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from tada.application.ports import StatusSink
from tada.cli.display.theme import ISSUE_SEVERITY_STYLE, SECTION_STATE_STYLE
from tada.graph.events import (
    SECTION_COMPLETE_STATES,
    GraphStatusEvent,
    GraphStatusStore,
    IssueSeverity,
    LLMUsage,
    Status,
    StatusIssue,
)

SECTIONS_TITLE = "Sections"
SECTIONS_RUNNING_TEXT = "Documenting workbook..."
ISSUES_TITLE = "Issues"
SUMMARY_TITLE = "Summary"
SUMMARY_RUNNING_TEXT = "Generating summary..."
SUMMARY_DONE_TEXT = "Summary generated"


class DocumentationProgressDisplay:
    def __init__(self, total_sections: int) -> None:
        self.section_progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} sections"),
            TimeElapsedColumn(),
        )
        self.section_task_id = self.section_progress.add_task(
            SECTIONS_RUNNING_TEXT,
            total=total_sections,
        )

    def render(self, store: GraphStatusStore) -> Group:
        self._sync_progress(store)

        items = [
            Rule(SECTIONS_TITLE, style="bold blue"),
            self._build_sections_table(store),
            Text(""),
            self.section_progress,
        ]

        issues_table = self._build_issues_table(store)
        if issues_table is not None:
            items.extend(
                [
                    Text(""),
                    Rule(ISSUES_TITLE, style="bold yellow"),
                    issues_table,
                ]
            )

        return Group(*items)

    def _format_token_count(self, usage: LLMUsage) -> str:
        return f"{usage.total_tokens:,}" if usage.total_tokens > 0 else "-"

    def _format_total_cost_usd(self, usage: LLMUsage) -> str:
        return f"${usage.total_cost_usd:.4f}" if usage.total_cost_usd > 0 else "-"

    def _build_sections_table(self, store: GraphStatusStore) -> Table:
        tbl = Table(
            show_header=True,
            header_style="bold blue",
            box=None,
            padding=(0, 1),
        )
        tbl.add_column("Step", no_wrap=True, width=14)
        tbl.add_column("Status", no_wrap=True, width=24)
        tbl.add_column("Attempts", no_wrap=True, width=8)
        tbl.add_column("Issues", no_wrap=True, width=12)
        tbl.add_column("Token Count", no_wrap=True, width=12)
        tbl.add_column("Total Cost (USD)", no_wrap=True, width=12)

        for sec_name, sec_status in store.sections.items():
            color = SECTION_STATE_STYLE.get(sec_status.state, "white")
            section_status_element = Text(
                sec_status.state.name.replace("_", " ").title(),
                style=color,
                no_wrap=True,
            )

            token_count_element = self._format_token_count(sec_status.llm_usage)
            total_cost_element = self._format_total_cost_usd(sec_status.llm_usage)

            tbl.add_row(
                sec_name,
                section_status_element,
                str(sec_status.attempts) if sec_status.attempts > 0 else "-",
                self._format_issue_count(sec_status),
                token_count_element,
                total_cost_element,
            )

        return tbl

    def _build_issues_table(self, store: GraphStatusStore) -> Table | None:
        issue_rows = self._collect_issue_rows(store)

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
            style = ISSUE_SEVERITY_STYLE.get(issue.severity, "white")

            table.add_row(
                step_name,
                Text(issue.severity.name.title(), style=style, no_wrap=True),
                issue.code or "-",
                issue.message,
            )

        return table

    def _collect_issue_rows(
        self,
        store: GraphStatusStore,
    ) -> list[tuple[str, StatusIssue]]:
        rows: list[tuple[str, StatusIssue]] = []

        section_order = {
            section_name: index
            for index, section_name in enumerate(store.sections.keys())
        }

        for section_name, section_status in store.sections.items():
            # Only want to surface error details for completed sections
            if section_status.state not in SECTION_COMPLETE_STATES:
                continue

            for issue in section_status.issues:
                # Only display INFO e.g. skipped empty section & blocking errors to
                # reduce non-blocking warning noise
                if issue.severity != IssueSeverity.WARNING:
                    rows.append((section_name, issue))

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
        return (
            -int(issue.severity),  # Descending order ERROR=3 -> WARNING=2 -> INFO=1
            section_order.get(section_name, 999),
            issue.code or "",
            issue.message,
        )

    def _format_issue_count(self, status: Status) -> Text:
        if not status.issues:
            return Text("-")

        counts = Counter(issue.severity for issue in status.issues)

        parts: list[Text] = []

        if counts[IssueSeverity.ERROR]:
            parts.append(Text(f"E:{counts[IssueSeverity.ERROR]}", style="red"))
        if counts[IssueSeverity.WARNING]:
            parts.append(Text(f"W:{counts[IssueSeverity.WARNING]}", style="yellow"))
        if counts[IssueSeverity.INFO]:
            parts.append(Text(f"I:{counts[IssueSeverity.INFO]}", style="blue"))

        return Text(" ").join(parts) if parts else Text("-")

    def _sync_progress(self, store: GraphStatusStore) -> None:
        completed_sections = sum(
            1
            for status in store.sections.values()
            if status.state in SECTION_COMPLETE_STATES
        )

        self.section_progress.update(
            self.section_task_id,
            completed=completed_sections,
        )


class RichDocumentationProgressSink(StatusSink):
    """Applies graph status events and refreshes the Rich live display."""

    def __init__(
        self,
        *,
        display: DocumentationProgressDisplay,
        store: GraphStatusStore,
        live: Live,
    ) -> None:
        self.display = display
        self.store = store
        self.live = live

    def handle(self, event: GraphStatusEvent) -> None:
        self.store.apply(event)
        self.refresh()

    def refresh(self) -> None:
        self.live.update(self.display.render(self.store))

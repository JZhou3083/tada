from dataclasses import dataclass, field
from enum import IntEnum, StrEnum

from tada.llm.schemas import EvalResult


class StepKind(StrEnum):
    SECTION = "section"
    SUMMARY = "summary"


class IssueSeverity(IntEnum):
    INFO = 1
    WARNING = 2
    ERROR = 3


class SectionState(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    EVALUATING = "evaluating"
    RETRYING = "retrying"
    SKIPPED = "skipped"
    FAILED = "failed"  # Currently unused but may help when catching other exceptions
    REACHED_RETRY_LIMIT = "reached_retry_limit"
    DONE = "done"


SECTION_COMPLETE_STATES = {
    SectionState.DONE,
    SectionState.FAILED,
    SectionState.REACHED_RETRY_LIMIT,
    SectionState.SKIPPED,
}


@dataclass(frozen=True)
class StatusIssue:
    message: str
    severity: IssueSeverity = IssueSeverity.WARNING
    code: str | None = None
    source: str | None = None  # e.g. "eval", "google_api"


@dataclass(frozen=True)
class Status:
    state: SectionState = SectionState.PENDING
    attempts: int = 0
    issues: tuple[StatusIssue, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StatusUpdate:
    state: SectionState | None = None
    attempts: int | None = None

    # None = preserve existing issues
    # () = clear issues
    # (...) = replace issues
    issues: tuple[StatusIssue, ...] | None = None


@dataclass(frozen=True)
class GraphStatusEvent:
    name: str
    kind: StepKind
    update: StatusUpdate


@dataclass
class GraphStatusStore:
    sections: dict[str, Status] = field(default_factory=dict)
    summary: Status | None = None

    def apply(self, event: GraphStatusEvent) -> None:
        match event.kind:
            case StepKind.SECTION:
                current = self.sections.get(event.name)
                self.sections[event.name] = self._merge_status(current, event.update)

            case StepKind.SUMMARY:
                self.summary = self._merge_status(self.summary, event.update)

    def _merge_status(
        self,
        current: Status | None,
        update: StatusUpdate,
    ) -> Status:
        current = current or Status()

        return Status(
            state=update.state if update.state is not None else current.state,
            attempts=update.attempts
            if update.attempts is not None
            else current.attempts,
            issues=update.issues if update.issues is not None else current.issues,
        )


def issues_from_eval_result(eval_result: EvalResult) -> tuple[StatusIssue, ...]:
    issues: list[StatusIssue] = []

    for issue in eval_result.blocking_issues:
        issues.append(
            StatusIssue(
                message=issue.item,
                severity=IssueSeverity.ERROR,
                code=issue.type,
                source="eval",
            )
        )

    for issue in eval_result.non_blocking_issues:
        issues.append(
            StatusIssue(
                message=issue.item,
                severity=IssueSeverity.WARNING,
                code=issue.type,
                source="eval",
            )
        )

    return tuple(issues)

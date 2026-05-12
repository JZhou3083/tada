from dataclasses import dataclass, field
from enum import StrEnum


class StepKind(StrEnum):
    SECTION = "section"
    SUMMARY = "summary"


class IssueSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SectionState(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    EVALUATING = "evaluating"
    RETRYING = "retrying"
    REACHED_RETRY_LIMIT = "reached_retry_limit"
    DONE = "done"


@dataclass(frozen=True)
class StatusIssue:
    message: str
    severity: IssueSeverity = IssueSeverity.WARNING
    code: str | None = None


@dataclass(frozen=True)
class Status:
    state: SectionState = SectionState.PENDING
    attempts: int = 0
    issues: tuple[StatusIssue, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GraphStatusEvent:
    name: str
    kind: StepKind
    status: Status


@dataclass
class GraphStatusStore:
    sections: dict[str, Status] = field(default_factory=dict)
    summary: Status | None = None

    def apply(self, event: GraphStatusEvent) -> None:
        match event.kind:
            case StepKind.SECTION:
                self.sections[event.name] = event.status
            case StepKind.SUMMARY:
                self.summary = event.status

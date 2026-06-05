from dataclasses import dataclass, field
from decimal import Decimal
from enum import IntEnum, StrEnum
from typing import Iterable, Self


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
    FAILED = "failed"
    REACHED_RETRY_LIMIT = "reached_retry_limit"
    DONE = "done"


@dataclass(frozen=True)
class StatusIssue:
    message: str
    severity: IssueSeverity = IssueSeverity.WARNING
    code: str | None = None
    source: str | None = None  # e.g. "eval", "google_api"


@dataclass(frozen=True)
class LLMUsage:
    total_tokens: int = 0
    total_cost_usd: Decimal = Decimal("0")

    def __add__(self, other: "LLMUsage") -> "LLMUsage":
        return LLMUsage(
            total_tokens=self.total_tokens + other.total_tokens,
            total_cost_usd=self.total_cost_usd + other.total_cost_usd,
        )


@dataclass(frozen=True)
class Status:
    state: SectionState = SectionState.PENDING
    attempt: int = 0
    issues: tuple[StatusIssue, ...] = field(default_factory=tuple)
    llm_usage: LLMUsage = field(default_factory=LLMUsage)


@dataclass(frozen=True)
class StatusUpdate:
    state: SectionState | None = None
    attempt: int | None = None
    issues: tuple[StatusIssue, ...] | None = None
    llm_usage: LLMUsage | None = None


@dataclass(frozen=True)
class GraphStatusEvent:
    graph_name: str
    section_name: str
    update: StatusUpdate


@dataclass
class GraphStatusStore:
    sections: dict[str, Status] = field(default_factory=dict)

    def apply(self, event: GraphStatusEvent) -> None:
        current = self.sections.get(event.section_name)
        self.sections[event.section_name] = self._merge_status(current, event.update)

    def _merge_status(
        self,
        current: Status | None,
        update: StatusUpdate,
    ) -> Status:
        current = current or Status()

        updated_state = update.state if update.state is not None else current.state
        updated_attempts = (
            update.attempt if update.attempt is not None else current.attempt
        )
        updated_issues = update.issues if update.issues is not None else current.issues
        updated_llm_usage = (
            (current.llm_usage + update.llm_usage)
            if update.llm_usage
            else current.llm_usage
        )

        return Status(
            state=updated_state,
            attempt=updated_attempts,
            issues=updated_issues,
            llm_usage=updated_llm_usage,
        )

    @classmethod
    def from_sections(cls, sections: Iterable[str]) -> Self:
        return cls(sections={s: Status() for s in sections})

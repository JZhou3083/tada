from dataclasses import dataclass
from enum import Enum

# TODO: can we add additional information like reached maximum attempts? # issues etc.?


class SectionState(Enum):
    PENDING = "pending"
    GENERATING = "generating"
    EVALUATING = "evaluating"
    RETRYING = "retrying"
    DONE = "done"


@dataclass(frozen=True)
class Status:
    state: SectionState = SectionState.PENDING
    attempts: int = 0


@dataclass(frozen=True)
class GraphStatusEvent:
    section: str
    status: Status

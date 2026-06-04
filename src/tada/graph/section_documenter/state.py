import operator
from typing import Annotated, Any, TypedDict

from tada.domain.sections import WorkbookSection
from tada.graph.schemas import LLMCallRecord
from tada.llm.schemas import EvalResult


# TODO: replace section enum with pure string...?
class SectionDocumenterInput(TypedDict):
    section: WorkbookSection
    data: dict[str, Any]
    prompt: str
    response_template: str


class SectionDocumenterOutput(TypedDict):
    docs_by_section: dict[WorkbookSection, str]
    llm_calls: Annotated[list[LLMCallRecord], operator.add]


class SectionDocumenterState(SectionDocumenterInput, SectionDocumenterOutput):
    skip_section: bool
    generation_attempts: int
    generated_section_doc: str
    evaluation_history: Annotated[list[EvalResult], operator.add]


def get_latest_eval_result(
    state: SectionDocumenterState,
) -> EvalResult | None:
    history = state.get("evaluation_history", [])
    return history[-1] if history else None

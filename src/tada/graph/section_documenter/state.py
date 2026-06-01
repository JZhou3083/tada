import operator

# from decimal import Decimal
from typing import Annotated, Any, TypedDict

from tada.domain.sections import WorkbookSection
from tada.llm.schemas import EvalResult


class SectionDocumenterInput(TypedDict):
    section: WorkbookSection
    data: dict[str, Any]
    prompt: str
    response_template: str


class SectionDocumenterOutput(TypedDict):
    docs_by_section: dict[WorkbookSection, str]
    # TODO: carry cost breakdown through graph and into final result
    # cost_breakdown: dict[WorkbookSection, dict[str, Decimal]]


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

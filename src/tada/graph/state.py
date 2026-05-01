from typing import Annotated, Any, NotRequired, TypedDict

from tada.domain.workbook import Workbook, WorkbookSection
from tada.llm.schemas import EvalResult


class InputState(TypedDict):
    workbook: Workbook
    generation_plan: list[WorkbookSection]


class OutputState(TypedDict):
    final_doc: str


def merge_dicts(a: dict, b: dict) -> dict:
    return a | b


class OverallState(InputState, OutputState):
    # section_docs is an internal field not exposed in either input or output
    section_docs: Annotated[
        dict[WorkbookSection, str],
        merge_dicts,
    ]


class SectionDocumenterState(TypedDict):
    section: WorkbookSection
    data: dict[str, Any]
    prompt: str
    response_template: str
    generated_docs: NotRequired[str]
    evaluation: NotRequired[EvalResult]
    attempts: int

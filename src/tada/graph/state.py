import operator
from typing import Annotated, Any, TypedDict

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


class SectionDocumenterInput(TypedDict):
    section: WorkbookSection
    data: dict[str, Any]
    prompt: str
    response_template: str


class SectionDocumenterOutput(TypedDict):
    section_docs: dict[WorkbookSection, str]


class SectionDocumenterState(SectionDocumenterInput, SectionDocumenterOutput):
    generated_docs: str
    evaluation_history: Annotated[list[EvalResult], operator.add]
    attempts: int

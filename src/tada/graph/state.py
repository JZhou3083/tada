import operator
from typing import Annotated, Any, TypedDict

from tada.domain.workbook import Workbook, WorkbookSection
from tada.llm.schemas import EvalResult


class InputState(TypedDict):
    workbook: Workbook
    generation_plan: list[WorkbookSection]
    run_summary_step: bool


class OutputState(TypedDict):
    final_doc: str


def merge_dicts(a: dict, b: dict) -> dict:
    return a | b


class OverallState(InputState, OutputState):
    # docs_by_section is an internal field not exposed in either input or output
    docs_by_section: Annotated[
        dict[WorkbookSection, str],
        merge_dicts,
    ]


class SectionDocumenterInput(TypedDict):
    section: WorkbookSection
    data: dict[str, Any]
    prompt: str
    response_template: str


class SectionDocumenterOutput(TypedDict):
    docs_by_section: dict[WorkbookSection, str]


class SectionDocumenterState(SectionDocumenterInput, SectionDocumenterOutput):
    skip_section: bool
    generation_attempts: int
    generated_section_doc: str
    evaluation_history: Annotated[list[EvalResult], operator.add]

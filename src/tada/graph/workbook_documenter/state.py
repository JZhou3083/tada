import operator
from typing import Annotated, TypedDict

from tada.domain.sections import WorkbookSection
from tada.domain.workbook import Workbook
from tada.graph.schemas import LLMCallEvent


def merge_dicts(a: dict, b: dict) -> dict:
    overlap = set(a).intersection(b)
    if overlap:
        raise ValueError(f"Duplicate docs_by_section keys: {overlap}")
    return a | b


class WorkbookDocumenterInput(TypedDict):
    workbook: Workbook
    generation_plan: list[WorkbookSection]
    run_summary_step: bool


class WorkbookDocumenterOutput(TypedDict):
    final_doc: str
    llm_calls: Annotated[list[LLMCallEvent], operator.add]


class WorkbookDocumenterState(WorkbookDocumenterInput, WorkbookDocumenterOutput):
    # docs_by_section is an internal field not exposed in either input or output
    docs_by_section: Annotated[
        dict[WorkbookSection, str],
        merge_dicts,
    ]

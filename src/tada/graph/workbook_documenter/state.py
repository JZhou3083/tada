import operator
from typing import Annotated, TypedDict

from tada.domain.sections import WorkbookSection
from tada.domain.workbook import Workbook
from tada.graph.schemas import LLMCallEvent


def merge_section_docs(
    a: dict[WorkbookSection, str],
    b: dict[WorkbookSection, str],
) -> dict[WorkbookSection, str]:
    overlap = set(a).intersection(b)
    if overlap:
        raise ValueError(
            f"Duplicate section docs for: {', '.join(section.value for section in overlap)}"
        )
    return a | b


class WorkbookDocumenterInput(TypedDict):
    workbook: Workbook
    sections_to_document: list[WorkbookSection]
    include_summary: bool


class WorkbookDocumenterOutput(TypedDict):
    final_doc: str
    llm_calls: Annotated[list[LLMCallEvent], operator.add]


class WorkbookDocumenterState(WorkbookDocumenterInput, WorkbookDocumenterOutput):
    docs_by_section: Annotated[
        dict[WorkbookSection, str],
        merge_section_docs,
    ]

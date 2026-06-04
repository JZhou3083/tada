import operator
from typing import Annotated, TypedDict

from tada.domain.sections import WorkbookSection
from tada.domain.workbook import Workbook
from tada.graph.schemas import LLMCallRecord


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
    llm_calls: Annotated[list[LLMCallRecord], operator.add]


class WorkbookDocumenterState(WorkbookDocumenterInput, total=False):
    docs_by_section: Annotated[
        dict[WorkbookSection, str],
        merge_section_docs,
    ]
    final_doc: str
    llm_calls: Annotated[list[LLMCallRecord], operator.add]


def require_docs_by_section(
    state: WorkbookDocumenterState,
) -> dict[WorkbookSection, str]:
    docs = state.get("docs_by_section")
    if docs is None:
        raise ValueError(
            "docs_by_section is required after section documentation has run"
        )
    return docs

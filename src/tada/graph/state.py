from __future__ import annotations

from typing import Annotated, TypedDict

from tada.domain.workbook import Workbook
from tada.domain.workbook_sections import WorkbookSection


def merge_dicts(a: dict, b: dict) -> dict:
    return {**a, **b}


class State(TypedDict):
    workbook: Workbook
    generation_plan: list[WorkbookSection]
    generated_docs: Annotated[dict[str, str], merge_dicts]


class SectionSummarizerState(TypedDict):
    workbook: Workbook
    generated_docs: Annotated[dict[WorkbookSection, str], merge_dicts]
    section_id: WorkbookSection


class StateUpdate(TypedDict, total=False):
    generation_plan: list[str]
    generated_docs: dict[WorkbookSection, str]

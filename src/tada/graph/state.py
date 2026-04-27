from __future__ import annotations

from typing import Annotated, NotRequired, TypedDict

from tada.domain.workbook import Workbook
from tada.domain.workbook_sections import WorkbookSection


def merge_dicts(a: dict, b: dict) -> dict:
    return {**a, **b}


class State(TypedDict):
    workbook: Workbook
    generation_plan: list[WorkbookSection]
    generated_summaries: Annotated[NotRequired[dict[str, str]], merge_dicts]
    final_doc: NotRequired[str]


class SectionSummarizerState(TypedDict):
    workbook: Workbook
    section_id: WorkbookSection


class StateUpdate(TypedDict, total=False):
    generated_summaries: dict[WorkbookSection, str]
    final_doc: str

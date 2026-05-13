from typing import Annotated, TypedDict

from tada.domain.sections import WorkbookSection
from tada.domain.workbook import Workbook


def merge_dicts(a: dict, b: dict) -> dict:
    return a | b


class InputState(TypedDict):
    workbook: Workbook
    generation_plan: list[WorkbookSection]
    run_summary_step: bool


class OutputState(TypedDict):
    final_doc: str


class OverallState(InputState, OutputState):
    # docs_by_section is an internal field not exposed in either input or output
    docs_by_section: Annotated[
        dict[WorkbookSection, str],
        merge_dicts,
    ]

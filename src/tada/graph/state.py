from typing import Annotated, Any, TypedDict

from tada.domain.workbook import Workbook, WorkbookSection


class InputState(TypedDict):
    workbook: Workbook
    generation_plan: list[WorkbookSection]


class OutputState(TypedDict):
    final_doc: str


def merge_dicts(a: dict, b: dict) -> dict:
    return a | b


class OverallState(InputState, OutputState):
    # Generated summaries is an internal field not exposed in either input or output
    generated_summaries: Annotated[
        dict[WorkbookSection, str],
        merge_dicts,
    ]


class SectionSummarizerState(TypedDict):
    section: WorkbookSection
    data: dict[str, Any]
    prompt: str
    response_template: str

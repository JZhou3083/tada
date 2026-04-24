from __future__ import annotations

from typing import Annotated, TypedDict

from tada.domain.workbook import Workbook


def merge_dicts(a: dict, b: dict) -> dict:
    return {**a, **b}


class State(TypedDict):
    workbook: Workbook
    generation_plan: list[str]
    generated_docs: Annotated[dict[str, str], merge_dicts]


class ComponentSummarizerState(TypedDict):
    workbook: Workbook
    generated_docs: Annotated[dict[str, str], merge_dicts]
    component_id: str


class StateUpdate(TypedDict, total=False):
    generation_plan: list[str]
    generated_docs: dict[str, str]

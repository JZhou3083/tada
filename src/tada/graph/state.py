from __future__ import annotations

from typing import NotRequired, TypedDict

from tada.domain.workbook import Workbook


class State(TypedDict):
    workbook: Workbook
    response: NotRequired[str]


class StateUpdate(TypedDict, total=False):
    query: str
    response: str

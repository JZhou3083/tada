from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel


class Workbook(BaseModel):
    name: str
    datasources: Any
    actions: Any

    @classmethod
    def from_file(cls, file: Path) -> Self:
        return cls(name=file.name, datasources=None, actions=None)

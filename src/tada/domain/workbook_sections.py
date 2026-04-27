from __future__ import annotations

from enum import Enum
from typing import Any

from tada.domain.workbook import Workbook


class WorkbookSection(str, Enum):
    DATASOURCES = "datasources"
    CALCULATIONS = "calculations"
    DASHBOARDS = "dashboards"
    WORKSHEETS = "worksheets"
    ACTIONS = "actions"
    PARAMETERS = "parameters"
    TABLES = "tables"

    def fetch_from(self, workbook: Workbook) -> Any:
        """Return the corresponding attribute from a Workbook object."""
        return getattr(workbook, self.value)

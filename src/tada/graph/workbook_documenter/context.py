from __future__ import annotations

from dataclasses import dataclass

from tada.graph.section_documenter.context import SectionDocumenterContext
from tada.graph.workbook_documenter.settings import (
    WorkbookDocumenterSettings,
)


@dataclass(frozen=True)
class WorkbookDocumenterContext(SectionDocumenterContext):
    workbook_settings: WorkbookDocumenterSettings

from dataclasses import dataclass

from tada.graph.context import BaseDocumenterContext
from tada.graph.section_documenter.settings import (
    SectionDocumenterSettings,
    default_section_documenter_settings,
)
from tada.graph.workbook_documenter.settings import (
    WorkbookDocumenterSettings,
    default_workbook_documenter_settings,
)
from tada.llm.gateway import VertexAIGateway


@dataclass(frozen=True)
class WorkbookDocumenterContext(BaseDocumenterContext):
    workbook_settings: WorkbookDocumenterSettings


def create_workbook_documenter_context(
    *,
    gateway: VertexAIGateway,
    section_settings: SectionDocumenterSettings | None = None,
    workbook_settings: WorkbookDocumenterSettings | None = None,
) -> WorkbookDocumenterContext:
    """Create section documenter context, using default settings when omitted."""
    return WorkbookDocumenterContext(
        gateway=gateway,
        section_settings=section_settings or default_section_documenter_settings(),
        workbook_settings=workbook_settings or default_workbook_documenter_settings(),
    )

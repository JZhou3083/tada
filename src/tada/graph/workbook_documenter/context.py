from dataclasses import dataclass

from tada.graph.context import BaseDocumenterContext
from tada.graph.section_documenter.settings import (
    SectionDocumenterSettings,
)
from tada.graph.workbook_documenter.settings import (
    WorkbookDocumenterSettings,
)
from tada.llm.gateway import VertexAIGateway
from tada.settings import get_settings


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
    app_settings = get_settings()

    return WorkbookDocumenterContext(
        gateway=gateway,
        section_settings=section_settings or app_settings.graph.section_documenter,
        workbook_settings=workbook_settings or app_settings.graph.workbook_documenter,
    )

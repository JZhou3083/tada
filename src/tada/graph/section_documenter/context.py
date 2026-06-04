from dataclasses import dataclass

from tada.graph.context import BaseDocumenterContext
from tada.graph.section_documenter.settings import SectionDocumenterSettings
from tada.llm.gateway import VertexAIGateway
from tada.settings import get_settings


@dataclass(frozen=True)
class SectionDocumenterContext(BaseDocumenterContext):
    pass


def create_section_documenter_context(
    *,
    gateway: VertexAIGateway,
    section_settings: SectionDocumenterSettings | None = None,
) -> SectionDocumenterContext:
    """Create section documenter context, using default settings when omitted."""
    app_settings = get_settings()

    return SectionDocumenterContext(
        gateway=gateway,
        section_settings=section_settings or app_settings.graph.section_documenter,
    )

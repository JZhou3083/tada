from dataclasses import dataclass

from tada.graph.context import BaseDocumenterContext
from tada.graph.section_documenter.settings import (
    SectionDocumenterSettings,
    default_section_documenter_settings,
)
from tada.llm.gateway import VertexAIGateway


@dataclass(frozen=True)
class SectionDocumenterContext(BaseDocumenterContext):
    pass


def create_section_documenter_context(
    *,
    gateway: VertexAIGateway,
    section_settings: SectionDocumenterSettings | None = None,
) -> SectionDocumenterContext:
    """Create section documenter context, using default settings when omitted."""
    return SectionDocumenterContext(
        gateway=gateway,
        section_settings=section_settings or default_section_documenter_settings(),
    )

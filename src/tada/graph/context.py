from dataclasses import dataclass

from tada.graph.section_documenter.settings import (
    SectionDocumenterSettings,
)
from tada.llm.gateway import VertexAIGateway


@dataclass(frozen=True)
class BaseDocumenterContext:
    gateway: VertexAIGateway
    section_settings: SectionDocumenterSettings

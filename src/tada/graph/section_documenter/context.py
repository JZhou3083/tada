from __future__ import annotations

from dataclasses import dataclass

from tada.graph.section_documenter.settings import (
    SectionDocumenterSettings,
)
from tada.llm.gateway import LLMGateway


@dataclass(frozen=True)
class SectionDocumenterContext:
    gateway: LLMGateway
    section_settings: SectionDocumenterSettings

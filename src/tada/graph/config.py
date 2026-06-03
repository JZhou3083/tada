from dataclasses import dataclass

from tada.llm.gateway import VertexAIGateway

MAX_SECTION_ATTEMPTS = 2

AI_NOTICE = """> **AI-generated documentation notice**
>
> This documentation was generated with the assistance of an AI system using Tableau workbook metadata.
> It reflects the structure and logic present in the source file at the time of generation and does not validate business intent, analytical correctness, or data quality.
> Dashboard owners remain responsible for review and approval.
"""


@dataclass(frozen=True)
class SectionDocumenterConfig:
    max_section_attempts: int
    generation_model: str
    evaluation_model: str


@dataclass(frozen=True)
class WorkbookDocumenterConfig:
    section_config: SectionDocumenterConfig
    summary_model: str
    run_summary_step: bool


@dataclass
class GraphContext:
    gateway: VertexAIGateway

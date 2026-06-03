from dataclasses import dataclass

from tada.graph.section_documenter.settings import (
    SectionDocumenterSettings,
    default_section_documenter_settings,
)
from tada.graph.workbook_documenter.settings import (
    WorkbookDocumenterSettings,
    default_workbook_documenter_settings,
)
from tada.llm.gateway import VertexAIGateway, get_vertexai_gateway


@dataclass
class GraphContext:
    gateway: VertexAIGateway
    section_settings: SectionDocumenterSettings
    workbook_settings: WorkbookDocumenterSettings | None = None


def default_graph_context() -> GraphContext:
    return GraphContext(
        gateway=get_vertexai_gateway(),
        section_settings=default_section_documenter_settings(),
        workbook_settings=default_workbook_documenter_settings(),
    )

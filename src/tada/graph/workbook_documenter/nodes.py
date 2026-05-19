import logging
from importlib import resources

from tada.domain.sections import WorkbookSection
from tada.graph.config import AI_NOTICE
from tada.graph.events import SectionState
from tada.graph.helpers import StepKind, emit_graph_status
from tada.graph.workbook_documenter.state import OutputState, OverallState
from tada.llm.client import get_vertexai_gateway
from tada.llm.configs import build_base_generation_config

logger = logging.getLogger(__name__)


# Section order is mirrored from doc-agent repo config.yaml
# TODO: investigate whether we actually need to pass the summariser all sections
SECTION_ORDER = [
    WorkbookSection.DATASOURCES,
    WorkbookSection.CALCULATIONS,
    WorkbookSection.DASHBOARDS,
    WorkbookSection.WORKSHEETS,
    WorkbookSection.ACTIONS,
    WorkbookSection.PARAMETERS,
    WorkbookSection.TABLES,
]


def summarize_all_sections_documentation(state: OverallState) -> OutputState:
    docs_by_section = state["docs_by_section"]
    ordered_section_docs = [
        docs_by_section[s] for s in SECTION_ORDER if s in docs_by_section
    ]
    compiled_doc = "\\pagebreak\n\n".join(ordered_section_docs)

    logger.debug(
        "Compiled %d section docs into one document chars=%d",
        len(docs_by_section),
        len(compiled_doc),
    )

    final_doc_parts = ordered_section_docs

    if state["run_summary_step"]:
        emit_graph_status(
            name="summary",
            kind=StepKind.SUMMARY,
            state=SectionState.GENERATING,
        )

        summariser_prompt = (
            resources.files("tada") / "prompts" / "summariser.md"
        ).read_text(encoding="utf-8")

        client_wrapper = get_vertexai_gateway()

        contents = client_wrapper.contents_from_text_parts(
            [summariser_prompt, compiled_doc]
        )

        _, documentation_summary = client_wrapper.generate_text(
            model="gemini-3-flash-preview",
            contents=contents,
            config=build_base_generation_config(),
        )

        final_doc_parts = [documentation_summary] + ordered_section_docs

    emit_graph_status(
        name="summary",
        kind=StepKind.SUMMARY,
        state=SectionState.DONE,
    )

    return {
        "final_doc": "\n\n".join([p.rstrip() for p in [AI_NOTICE] + final_doc_parts])
    }

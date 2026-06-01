import logging
from importlib import resources

from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes

from tada.domain.sections import WorkbookSection
from tada.graph.config import AI_NOTICE
from tada.graph.events import SectionState
from tada.graph.helpers import StepKind, emit_graph_status
from tada.graph.workbook_documenter.state import OutputState, OverallState
from tada.llm.configs import build_base_generation_config
from tada.llm.gateway import get_vertexai_gateway
from tada.observability.otel.observe import observe

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


@observe(
    "langgraph.nodes.summarize_all_sections_documentation",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
    },
)
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

        gateway = get_vertexai_gateway()

        response = gateway.generate_text(
            model="gemini-3-flash-preview",
            contents=[summariser_prompt, compiled_doc],
            config=build_base_generation_config(),
        )

        # Update live display with token usage and cost info
        emit_graph_status(
            name="summary",
            kind=StepKind.SUMMARY,
            llm_response_metadata=response.metadata,
        )

        final_doc_parts = [response.content] + ordered_section_docs

    emit_graph_status(
        name="summary",
        kind=StepKind.SUMMARY,
        state=SectionState.DONE,
    )

    return {
        "final_doc": "\n\n".join([p.rstrip() for p in [AI_NOTICE] + final_doc_parts])
    }

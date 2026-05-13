import logging
import time
from importlib import resources

from tada.domain.sections import WorkbookSection
from tada.graph.config import AI_NOTICE
from tada.graph.events import SectionState
from tada.graph.helpers import StepKind, emit_graph_status
from tada.graph.workbook_documenter.state import OutputState, OverallState
from tada.llm.client import get_vertexai_gateway
from tada.llm.configs import build_base_generation_config

from langfuse import observe
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from tada.observability.langfuse_client import get_langfuse
from tada.observability.trace_printer import get_prop_attrs, update_generation
from tada.observability.reporter import log_span


langfuse = get_langfuse()

logger = logging.getLogger(__name__)


# Section order is mirrored from doc-agent repo config.yaml
# TODO: not all sections needed potentially
SECTION_ORDER = [
    WorkbookSection.DATASOURCES,
    WorkbookSection.CALCULATIONS,
    WorkbookSection.DASHBOARDS,
    WorkbookSection.WORKSHEETS,
    WorkbookSection.ACTIONS,
    WorkbookSection.PARAMETERS,
    WorkbookSection.TABLES,
]

@observe(name="summarize_all_sections", as_type="generation")
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

        try:
            client_wrapper = get_vertexai_gateway()

            span = trace.get_current_span()
            labels = get_prop_attrs(span.attributes) 

            contents = client_wrapper.contents_from_text_parts(
            [summariser_prompt, compiled_doc]
            )

            response, documentation_summary = client_wrapper.generate_text(
                model="gemini-3-flash-preview",
                contents=contents,
                config=build_base_generation_config(labels=labels),
            )
            span.set_status(StatusCode.OK)
        except Exception as e:
            span.set_status(StatusCode.ERROR, str(e))
            span.record_exception(e)
            raise

        update_generation(response=response,
                      langfuse=langfuse,
                      metadata={"section": ", ".join(s.value for s in docs_by_section)}
        )       

        final_doc_parts = [documentation_summary] + ordered_section_docs

    emit_graph_status(
        name="summary",
        kind=StepKind.SUMMARY,
        state=SectionState.DONE,
    )

    log_span(span=span)
    
    return {
        "final_doc": "\n\n".join([p.rstrip() for p in [AI_NOTICE] + final_doc_parts])
    }

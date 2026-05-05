import logging
import time
from importlib import resources

from tada.domain.workbook import WorkbookSection
from tada.graph.state import OutputState, OverallState
from tada.llm.client import get_vertexai_gateway
from tada.llm.configs import build_base_generation_config
from tada.llm.telemetry import log_genai_usage

logger = logging.getLogger(__name__)


# Section order is mirrored from doc-agent repo config.yaml
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
    section_docs = state["section_docs"]
    ordered_section_docs = [section_docs[s] for s in SECTION_ORDER if s in section_docs]
    compiled_doc = "\\pagebreak\n\n".join(ordered_section_docs)

    logger.debug(
        "Compiled %d section docs into one document chars=%d",
        len(section_docs),
        len(compiled_doc),
    )

    summariser_prompt = (
        resources.files("tada") / "prompts" / "summariser.md"
    ).read_text(encoding="utf-8")

    parts = [
        {"text": summariser_prompt},
        {"text": compiled_doc},
    ]
    contents = [{"role": "user", "parts": parts}]

    client_wrapper = get_vertexai_gateway()

    start = time.perf_counter()
    response, documentation_summary = client_wrapper.generate_text(
        model="gemini-3-flash-preview",
        contents=contents,
        config=build_base_generation_config(),
    )
    end = time.perf_counter()
    elapsed = end - start

    log_genai_usage(
        logger,
        response,
        label="compile",
        elapsed=elapsed,
        model="gemini-3-flash-preview",
    )

    final_doc_parts = [documentation_summary] + ordered_section_docs

    return {"final_doc": "\n\n".join([p.rstrip() for p in final_doc_parts])}

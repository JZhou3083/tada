import json
import logging
import time
from importlib import resources
from typing import TypedDict

from tada.clients.genai import (
    generate_text,
    get_compiled_doc_generation_config,
    get_section_summary_generation_config,
    log_genai_usage,
)
from tada.domain.workbook import WorkbookSection
from tada.graph.state import OutputState, OverallState, SectionSummarizerState

logger = logging.getLogger(__name__)


class SectionSummaryUpdate(TypedDict):
    section_summaries: dict[WorkbookSection, str]


# TODO: section summary needs to be a refinement loop with feedback instructions
def generate_section_summary(
    state: SectionSummarizerState,
) -> SectionSummaryUpdate:

    logger.debug("Beginning summary generation for %s", state["section"].value)

    parts = [
        {"text": state["prompt"]},
        {"text": state["response_template"]},
        {"text": json.dumps(state["data"])},
    ]
    payload = [{"role": "user", "parts": parts}]

    start = time.perf_counter()
    response, response_text = generate_text(
        model="gemini-3-flash-preview",
        contents=payload,
        config=get_section_summary_generation_config(),
    )
    end = time.perf_counter()
    elapsed = end - start

    log_genai_usage(
        logger,
        response,
        step="section",
        elapsed=elapsed,
        section=state["section"].value,
        model="gemini-3-flash-preview",
    )

    return {"section_summaries": {state["section"]: response_text}}


# Section order is somewhat arbitrary but intended to produce a compiled document
# to be passed to the LLM which gives an initial overview via dashboards and then goes
# increasingly into the details with tables and calculations coming later.
SECTION_ORDER = [
    WorkbookSection.DASHBOARDS,
    WorkbookSection.WORKSHEETS,
    WorkbookSection.ACTIONS,
    WorkbookSection.PARAMETERS,
    WorkbookSection.DATASOURCES,
    WorkbookSection.TABLES,
    WorkbookSection.CALCULATIONS,
]


def compile_summaries(state: OverallState) -> OutputState:
    summaries = state["section_summaries"]
    ordered_summaries = [summaries[s] for s in SECTION_ORDER if s in summaries]
    compiled_doc = "\\pagebreak\n\n".join(ordered_summaries)

    logger.debug(
        "Compiled %d section summaries into one document chars=%d",
        len(summaries),
        len(compiled_doc),
    )

    summariser_prompt = (
        resources.files("tada") / "prompts" / "summariser.md"
    ).read_text(encoding="utf-8")

    parts = [
        {"text": summariser_prompt},
        {"text": compiled_doc},
    ]
    payload = [{"role": "user", "parts": parts}]

    start = time.perf_counter()
    response, response_text = generate_text(
        model="gemini-3-flash-preview",
        contents=payload,
        config=get_compiled_doc_generation_config(),
    )
    end = time.perf_counter()
    elapsed = end - start

    log_genai_usage(
        logger,
        response,
        step="compile",
        elapsed=elapsed,
        model="gemini-3-flash-preview",
    )

    return {"final_doc": response_text}

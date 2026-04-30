import json
import logging
import time
from importlib import resources
from typing import TypedDict

from tada.clients.genai import (
    get_compiled_doc_generation_config,
    get_genai_client,
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

    response = get_genai_client().models.generate_content(
        model="gemini-3-flash-preview",
        contents=payload,
        config=get_section_summary_generation_config(),
    )
    response_text = str(response.text)

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


def compile_summaries(state: OverallState) -> OutputState:
    summaries = state["section_summaries"]
    ordered_summaries = [
        summaries[s]
        for s in [
            WorkbookSection.DASHBOARDS,
            WorkbookSection.WORKSHEETS,
            WorkbookSection.ACTIONS,
            WorkbookSection.PARAMETERS,
            WorkbookSection.DATASOURCES,
            WorkbookSection.TABLES,
            WorkbookSection.CALCULATIONS,
        ]
        if s in summaries
    ]
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

    response = get_genai_client().models.generate_content(
        model="gemini-3-flash-preview",
        contents=payload,
        config=get_compiled_doc_generation_config(),
    )
    response_text = str(response.text)

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

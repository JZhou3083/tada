import json
import logging
import time
from typing import TypedDict

from tada.clients.genai import get_genai_client, get_section_summary_generation_config
from tada.domain.workbook import WorkbookSection
from tada.graph.state import OutputState, OverallState, SectionSummarizerState

logger = logging.getLogger(__name__)


class SectionSummaryUpdate(TypedDict):
    generated_summaries: dict[WorkbookSection, str]


# TODO: section summary needs to be a refinement loop with feedback instructions
def generate_section_summary(
    state: SectionSummarizerState,
) -> SectionSummaryUpdate:

    logger.debug("Beginning summary generation for %s", state["section"].value)
    start = time.perf_counter()

    parts = [
        {"text": state["prompt"]},
        {"text": state["response_template"]},
        {"text": json.dumps(state["data"])},
    ]
    payload = [{"role": "user", "parts": parts}]

    response = get_genai_client().models.generate_content(
        model="gemini-3-flash-preview",
        contents=payload,
        config=get_section_summary_generation_config(),
    )
    response_text = str(response.text)

    end = time.perf_counter()
    elapsed = end - start

    um = getattr(response, "usage_metadata", None)

    logger.debug(
        (
            "Summary generation completed section=%s duration=%.3fs chars=%d "
            "tokens_total=%s tokens_prompt=%s tokens_output=%s tokens_tool=%s tokens_thoughts=%s "
            "tokens_cached=%s cache_hit=%s traffic_type=%s"
        ),
        state["section"].value,
        elapsed,
        len(response_text),
        getattr(um, "total_token_count", None),
        getattr(um, "prompt_token_count", None),
        getattr(um, "candidates_token_count", None),
        getattr(um, "tool_use_prompt_token_count", None),
        getattr(um, "thoughts_token_count", None),
        getattr(um, "cached_content_token_count", None),
        bool(getattr(um, "cached_content_token_count", 0) or 0),
        getattr(um, "traffic_type", None),
    )

    return {"generated_summaries": {state["section"]: response_text}}


def compile_summaries(state: OverallState) -> OutputState:
    summaries = state["generated_summaries"]
    logger.debug("Compiling all %d summaries...", len(summaries))

    ordered = [(s, summaries[s]) for s in state["generation_plan"] if s in summaries]

    formatted_sections = [
        f"# {section.value}\n{summary}" for section, summary in ordered
    ]
    compiled_doc = "\n\n".join(formatted_sections)

    logger.debug("Compiled %d summaries", len(summaries))
    return {"final_doc": compiled_doc}

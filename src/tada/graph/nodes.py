import json
import logging
import time
from importlib import resources
from typing import TypedDict

from google.genai import Client, types

from tada.domain.workbook import WorkbookSection
from tada.graph.state import OutputState, OverallState, SectionSummarizerState

logger = logging.getLogger(__name__)


class SectionSummaryUpdate(TypedDict):
    generated_summaries: dict[WorkbookSection, str]


def generate_section_summary(
    state: SectionSummarizerState,
) -> SectionSummaryUpdate:

    logger.debug("Beginning summary generation for %s", state["section"].value)
    start = time.perf_counter()

    client = Client(
        vertexai=True,
        project="jlr-dl-cat",
        location="global",
    )

    sys_instruction = (resources.files("tada") / "prompts" / "system.md").read_text(
        encoding="utf-8"
    )
    config = types.GenerateContentConfig(
        system_instruction=sys_instruction,
        temperature=0.2,
        top_p=0.2,
        seed=101,
        candidate_count=1,
        thinking_config=types.ThinkingConfig(
            include_thoughts=False, thinking_level=types.ThinkingLevel.LOW
        ),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    parts = [
        {"text": state["prompt"]},
        {"text": state["response_template"]},
        {"text": json.dumps(state["data"])},
    ]
    payload = [{"role": "user", "parts": parts}]

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=payload,
        config=config,
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

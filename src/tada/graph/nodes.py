import json
import logging
import time
from importlib import resources
from typing import Any

from tada.domain.workbook import WorkbookSection
from tada.graph.state import OutputState, OverallState, SectionDocumenterState
from tada.llm.client import get_vertexai_gateway
from tada.llm.configs import build_base_generation_config
from tada.llm.schemas import EvalResult
from tada.llm.telemetry import log_genai_usage

logger = logging.getLogger(__name__)


# TODO: rename things from summary to documentation
def generate_section_documentation(
    state: SectionDocumenterState,
) -> dict[str, Any]:
    logger.debug("Beginning documentation generation for %s", state["section"].value)

    parts = [
        {"text": state["prompt"]},
        {"text": state["response_template"]},
        {"text": json.dumps(state["data"])},
    ]
    contents = [{"role": "user", "parts": parts}]

    client_wrapper = get_vertexai_gateway()
    system_instruction = (resources.files("tada") / "prompts" / "system.md").read_text(
        encoding="utf-8"
    )

    start = time.perf_counter()
    response, section_docs = client_wrapper.generate_text(
        model="gemini-3-flash-preview",
        contents=contents,
        config=build_base_generation_config(system_instruction=system_instruction),
    )
    end = time.perf_counter()
    elapsed = end - start

    log_genai_usage(
        logger,
        response,
        label=f"{state['section'].value}:generate",
        elapsed=elapsed,
        model="gemini-3-flash-preview",
    )

    return {"generated_docs": section_docs}


def evaluate_section_documentation(state: SectionDocumenterState) -> dict[str, Any]:
    logger.debug("Beginning evaluation for %s", state["section"].value)

    if "generated_docs" not in state:
        raise ValueError("No documentation exists in state to summarize")

    evaluator_prompt = (
        resources.files("tada") / "prompts" / "evaluation.md"
    ).read_text(encoding="utf-8")

    parts = [
        {"text": evaluator_prompt},
        {"text": json.dumps(state["data"])},
        {"text": state["generated_docs"]},
        {"text": state["response_template"]},
    ]
    contents = [{"role": "user", "parts": parts}]

    client_wrapper = get_vertexai_gateway()

    start = time.perf_counter()
    response, evaluation = client_wrapper.generate_structured_response(
        model="gemini-3-flash-preview",
        contents=contents,
        schema_model=EvalResult,
        config=build_base_generation_config(),
    )
    end = time.perf_counter()
    elapsed = end - start

    log_genai_usage(
        logger,
        response,
        label=f"{state['section'].value}:evaluate",
        elapsed=elapsed,
        model="gemini-3-flash-preview",
    )

    return {"evaluation": evaluation}


def emit_section_documentation(state: SectionDocumenterState) -> dict[str, Any]:
    """Format results of documentation into a state update to remerge back into the parent branch"""
    if "generated_docs" not in state:
        raise ValueError("No docs yet generated")

    return {"section_docs": {state["section"]: state["generated_docs"]}}


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
    summaries = state["section_docs"]
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

    # TODO: final doc should actually also include each section not just the overall summary
    return {"final_doc": documentation_summary}

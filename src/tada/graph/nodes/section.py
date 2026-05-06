import json
import logging
import time
from importlib import resources
from typing import Any

from tada.graph.state import SectionDocumenterState
from tada.llm.client import get_vertexai_gateway
from tada.llm.configs import build_base_generation_config
from tada.llm.schemas import EvalResult
from tada.llm.telemetry import log_genai_usage

logger = logging.getLogger(__name__)


def _add_feedback_to_prompt(prompt: str, feedback: list[EvalResult]) -> str:
    feedback_history = [s.feedback_for_generator for s in feedback if not s.passed]
    if not feedback_history:
        return prompt

    if len(feedback_history) == 1:
        return (
            prompt
            + f"""### CRITICAL FEEDBACK (MUST FIX):
            The Quality Assurance team flagged the following errors in your previous attempt.
            You must ensure these are corrected in this new version:
            ---------------------------------------------------------
            {feedback_history[0]}
            (e.g., "You missed the calculated field 'Profit Ratio'. You hallucinated a 'Left Join'.")
            ---------------------------------------------------------
        """
        )

    latest_feedback = feedback_history[-1]
    older_feedback = "\n".join(f"- {fb}" for fb in feedback_history[:-1])

    return (
        prompt
        + f"""## CRITICAL FEEDBACK (MUST FIX):
                The Quality Assurance team identified issues in your previous attempts.
                Below is the full feedback history. Some of these items were already corrected in earlier revisions, but they are included here to ensure no issue reappears.
                ---------------------------------------------------------
                Most Recent Feedback (Must Fix NOW):
                {latest_feedback}
                ---------------------------------------------------------
                Past Feedback (Older Attempts):
                {older_feedback}
                ---------------------------------------------------------
                You must ensure:
                1. All items in the most recent feedback are fully corrected.
                2. No issues from past feedback reappear in this version.
            """
    )


def generate_section_documentation(
    state: SectionDocumenterState,
) -> dict[str, Any]:
    if "generation_attempts" not in state:
        state["generation_attempts"] = 0

    logger.debug(
        "Beginning generation node label=%s generation_attempt=%d",
        f"{state['section'].value}:generate",
        state["generation_attempts"] + 1,
    )

    full_prompt = state["prompt"]

    if "evaluation_history" in state:
        full_prompt = _add_feedback_to_prompt(full_prompt, state["evaluation_history"])

    parts = [
        {"text": full_prompt},
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

    return {
        "generated_section_doc": section_docs,
        "generation_attempts": state["generation_attempts"] + 1,
    }


def evaluate_section_documentation(state: SectionDocumenterState) -> dict[str, Any]:
    logger.debug(
        "Beginning evaluation node label=%s generation_attempt=%d",
        f"{state['section'].value}:evaluate",
        state.get("generation_attempts"),
    )

    if "generated_section_doc" not in state:
        raise ValueError("No documentation exists in state to evaluate")

    evaluator_prompt = (
        resources.files("tada") / "prompts" / "evaluation.md"
    ).read_text(encoding="utf-8")

    parts = [
        {"text": evaluator_prompt},
        {"text": json.dumps(state["data"])},
        {"text": state["generated_section_doc"]},
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

    return {"evaluation_history": [evaluation]}


def emit_section_documentation(state: SectionDocumenterState) -> dict[str, Any]:
    """Format results of documentation into a state update to remerge back into the parent branch"""
    if "generated_section_doc" not in state:
        raise ValueError(
            f"Cannot emit section documentation because generated_section_doc is missing. "
            f"section={state.get('section').value}, attempts={state.get('attempts')}"
        )

    return {"section_docs": {state["section"]: state["generated_section_doc"]}}

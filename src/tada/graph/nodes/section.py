import json
import logging
import time
from importlib import resources
from typing import Any

from tada.graph.events import SectionState, StepKind, issues_from_eval_result
from tada.graph.nodes.helpers import emit_graph_status
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
    # `generation_attempts` state var is not set on first generation
    if "generation_attempts" not in state:
        state["generation_attempts"] = 0
        emit_graph_status(
            name=state["section"].value,
            kind=StepKind.SECTION,
            state=SectionState.GENERATING,
            attempts=0,
            issues=(),
        )
    else:
        emit_graph_status(
            name=state["section"].value,
            kind=StepKind.SECTION,
            state=SectionState.RETRYING,
            attempts=state["generation_attempts"],
        )

    logger.debug(
        "Beginning generation node label=%s generation_attempt=%d",
        f"{state['section'].value}:generate",
        state["generation_attempts"] + 1,
    )

    full_prompt = state["prompt"]

    if "evaluation_history" in state:
        full_prompt = _add_feedback_to_prompt(full_prompt, state["evaluation_history"])

    client_wrapper = get_vertexai_gateway()
    system_instruction = (resources.files("tada") / "prompts" / "system.md").read_text(
        encoding="utf-8"
    )

    start = time.perf_counter()

    contents = client_wrapper.contents_from_text_parts(
        [full_prompt, state["response_template"], json.dumps(state["data"])]
    )
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
    )

    return {
        "generated_section_doc": section_docs,
        "generation_attempts": state["generation_attempts"] + 1,
    }


def evaluate_section_documentation(state: SectionDocumenterState) -> dict[str, Any]:
    emit_graph_status(
        name=state["section"].value,
        kind=StepKind.SECTION,
        state=SectionState.EVALUATING,
        attempts=state["generation_attempts"],
    )

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

    client_wrapper = get_vertexai_gateway()

    start = time.perf_counter()
    contents = client_wrapper.contents_from_text_parts(
        [
            evaluator_prompt,
            json.dumps(state["data"]),
            state["generated_section_doc"],
            state["response_template"],
        ]
    )
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
    )

    # Update graph status with any resulting issues / clear issues if there are none
    emit_graph_status(
        name=state["section"].value,
        kind=StepKind.SECTION,
        state=SectionState.EVALUATING,
        attempts=state["generation_attempts"],
        issues=issues_from_eval_result(evaluation),
    )

    return {"evaluation_history": [evaluation]}


def emit_section_documentation(state: SectionDocumenterState) -> dict[str, Any]:
    """Format results of documentation into a state update to remerge back into the parent branch"""
    emit_graph_status(
        name=state["section"].value,
        kind=StepKind.SECTION,
        state=SectionState.DONE,
        attempts=state["generation_attempts"],
    )

    if "generated_section_doc" not in state:
        raise ValueError(
            f"Cannot emit section documentation because generated_section_doc is missing. "
            f"section={state.get('section').value}, attempts={state.get('attempts')}"
        )

    return {"docs_by_section": {state["section"]: state["generated_section_doc"]}}


def emit_section_documentation_with_issues(
    state: SectionDocumenterState,
) -> dict[str, Any]:

    emit_graph_status(
        name=state["section"].value,
        kind=StepKind.SECTION,
        state=SectionState.REACHED_RETRY_LIMIT,
        attempts=state["generation_attempts"],
    )

    if "generated_section_doc" not in state:
        raise ValueError(
            f"Cannot emit section documentation because generated_section_doc is missing. "
            f"section={state.get('section').value}, attempts={state.get('attempts')}"
        )

    return {"docs_by_section": {state["section"]: state["generated_section_doc"]}}

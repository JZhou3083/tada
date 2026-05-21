import json
import logging
from functools import partial
from importlib import resources
from typing import Any

from tada.graph.events import (
    IssueSeverity,
    SectionState,
    StatusIssue,
    StepKind,
    issues_from_eval_result,
)
from tada.graph.helpers import emit_graph_status
from tada.graph.section_documenter.state import (
    SectionDocumenterInput,
    SectionDocumenterState,
    get_latest_eval_result,
)
from tada.llm.client import get_vertexai_gateway
from tada.llm.configs import build_base_generation_config
from tada.llm.schemas import EvalResult
from tada.observability.otel.observe import observe

logger = logging.getLogger(__name__)


def prepare_section(state: SectionDocumenterInput) -> dict[str, Any]:
    updates = {"generation_attempts": 0}

    # Skip all LLM generation - directly to emit - if payload is empty
    if not state.get("data"):
        emit_graph_status(
            name=state["section"].value,
            kind=StepKind.SECTION,
            state=SectionState.SKIPPED,
            attempts=0,
            issues=(
                StatusIssue(
                    "Generation skipped due to empty data payload.",
                    severity=IssueSeverity.INFO,
                    code="empty-payload",
                    source="graph",
                ),
            ),
        )
        return updates | {"skip_section": True}

    return updates | {"skip_section": False}


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


@observe("langgraph.nodes.generate_section_documentation")
def generate_section_documentation(
    state: SectionDocumenterState,
) -> dict[str, Any]:
    emit_graph_status(
        name=state["section"].value,
        kind=StepKind.SECTION,
        state=SectionState.GENERATING,
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

    contents = client_wrapper.contents_from_text_parts(
        [full_prompt, state["response_template"], json.dumps(state["data"])]
    )

    _, section_docs = client_wrapper.generate_text(
        model="gemini-3-flash-preview",
        contents=contents,
        config=build_base_generation_config(
            system_instruction=system_instruction,
        ),
    )

    return {
        "generated_section_doc": section_docs,
        "generation_attempts": state["generation_attempts"] + 1,
    }


@observe("langgraph.nodes.evaluate_section_documentation")
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

    contents = client_wrapper.contents_from_text_parts(
        [
            evaluator_prompt,
            json.dumps(state["data"]),
            state["generated_section_doc"],
            state["response_template"],
        ]
    )

    _, evaluation = client_wrapper.generate_structured_response(
        model="gemini-3-flash-preview",
        contents=contents,
        schema_model=EvalResult,
        config=build_base_generation_config(),
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


def format_blocking_issues_header(eval_result: EvalResult | None) -> str | None:
    if eval_result is None or not eval_result.blocking_issues:
        return None

    lines = [
        "> [!WARNING]",
        "> This section was emitted with unresolved blocking issues from the latest evaluation.",
        ">",
        "> Blocking issues:",
    ]

    for issue in eval_result.blocking_issues:
        lines.append(f"> - `{issue.type}`: {issue.item}")

    return "\n".join(lines)


def add_blocking_issues_header(
    *,
    doc: str,
    eval_result: EvalResult | None,
) -> str:
    header = format_blocking_issues_header(eval_result)

    if not header:
        return doc

    return f"{header}\n\n{doc}"


def _emit_section_documentation_generic(
    state: SectionDocumenterState,
    *,
    final_state: SectionState = SectionState.DONE,
    require_doc: bool = True,
    include_blocking_issues_header: bool = False,
) -> dict[str, Any]:
    """Format results of documentation into a state update to remerge back into the parent branch"""
    section = state["section"]
    attempts = state.get("generation_attempts", 0)
    doc = state.get("generated_section_doc")

    emit_graph_status(
        name=section.value,
        kind=StepKind.SECTION,
        state=final_state,
        attempts=attempts,
    )

    doc = state.get("generated_section_doc")

    if doc is None:
        if require_doc:
            raise ValueError(
                "Cannot emit section documentation because generated_section_doc is missing. "
                f"section={section.value}, attempts={attempts}, final_state={final_state}"
            )
        return {
            "docs_by_section": {},
        }

    if include_blocking_issues_header:
        doc = add_blocking_issues_header(
            doc=doc,
            eval_result=get_latest_eval_result(state),
        )

    return {"docs_by_section": {section: doc}}


emit_section_documentation = partial(
    _emit_section_documentation_generic,
    final_state=SectionState.DONE,
)

emit_section_documentation_retry_limit = partial(
    _emit_section_documentation_generic,
    final_state=SectionState.REACHED_RETRY_LIMIT,
    include_blocking_issues_header=True,
)

emit_section_documentation_skipped = partial(
    _emit_section_documentation_generic,
    final_state=SectionState.SKIPPED,
    require_doc=False,
)

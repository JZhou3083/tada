import json
from functools import partial
from typing import Any

import structlog
from langgraph.runtime import Runtime
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes

from tada.graph.events import (
    IssueSeverity,
    SectionState,
    StatusIssue,
    issues_from_eval_result,
)
from tada.graph.helpers import emit_graph_status
from tada.graph.schemas import LLMCallEvent
from tada.graph.section_documenter.context import SectionDocumenterContext
from tada.graph.section_documenter.document_markdown import (
    prepend_unresolved_blocking_issues_warning_md,
)
from tada.graph.section_documenter.prompts import append_eval_feedback_prompt
from tada.graph.section_documenter.state import (
    SectionDocumenterInput,
    SectionDocumenterState,
    get_latest_eval_result,
)
from tada.llm.configs import build_base_generation_config
from tada.llm.schemas import EvalResult
from tada.observability.otel.observe import observe
from tada.prompts import load_prompt

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def prepare_section(state: SectionDocumenterInput) -> dict[str, Any]:
    section = state["section"].value

    logger.info(
        "graph.node.started",
        node_name="prepare_section",
        section=section,
    )

    updates = {"generation_attempts": 0}

    # Skip all LLM generation - directly to emit - if payload is empty
    if not state.get("data"):
        emit_graph_status(
            name=state["section"].value,
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

        logger.info(
            "graph.node.skipped",
            node_name="prepare_section",
            section=section,
            skip_reason="empty_payload",
        )

        return updates | {"skip_section": True}

    logger.info(
        "graph.node.completed",
        node_name="prepare_section",
        section=section,
        skip_section=False,
    )

    return updates | {"skip_section": False}


@observe(
    "graph.node.generate_section_documentation",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
    },
)
def generate_section_documentation(
    state: SectionDocumenterState, runtime: Runtime[SectionDocumenterContext]
) -> dict[str, Any]:
    section = state["section"].value
    attempt = state["generation_attempts"] + 1

    logger.info(
        "graph.node.started",
        node_name="generate_section_documentation",
        section=section,
        attempt=attempt,
        has_evaluation_history="evaluation_history" in state,
    )

    emit_graph_status(
        name=state["section"].value,
        state=SectionState.GENERATING,
        attempts=attempt,
    )

    full_prompt = state["prompt"]

    if "evaluation_history" in state:
        full_prompt = append_eval_feedback_prompt(
            full_prompt, state["evaluation_history"]
        )

    system_instruction = load_prompt("system.md")

    response = runtime.context.gateway.generate_text(
        model=runtime.context.section_settings.documentation_model,
        contents=[full_prompt, state["response_template"], json.dumps(state["data"])],
        config=build_base_generation_config(
            system_instruction=system_instruction,
        ),
    )

    # Update the live token & cost tracking display
    emit_graph_status(
        name=state["section"].value,
        llm_response_metadata=response.metadata,
    )

    logger.info(
        "graph.node.completed",
        node_name="generate_section_documentation",
        section=section,
        attempt=attempt,
        model_name=response.metadata.model_name,
        elapsed_seconds=response.metadata.elapsed_seconds,
        input_tokens=response.metadata.input_tokens,
        output_tokens=response.metadata.output_tokens,
        total_tokens=response.metadata.total_tokens,
    )

    return {
        "generated_section_doc": response.content,
        "generation_attempts": attempt,
        "llm_calls": [
            LLMCallEvent(
                node_name="generate_section_documentation",
                metadata=response.metadata,
                section_subgraph=state["section"].value,
                section_attempt=attempt,
            )
        ],
    }


@observe(
    "graph.node.evaluate_section_documentation",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
    },
)
def evaluate_section_documentation(
    state: SectionDocumenterState, runtime: Runtime[SectionDocumenterContext]
) -> dict[str, Any]:
    section = state["section"].value
    attempt = state.get("generation_attempts")

    logger.info(
        "graph.node.started",
        node_name="evaluate_section_documentation",
        section=section,
        attempt=attempt,
        has_generated_doc="generated_section_doc" in state,
    )

    emit_graph_status(
        name=state["section"].value,
        state=SectionState.EVALUATING,
        attempts=state["generation_attempts"],
    )

    if "generated_section_doc" not in state:
        logger.error(
            "graph.node.validation_failed",
            node_name="evaluate_section_documentation",
            section=section,
            attempt=attempt,
            missing_field="generated_section_doc",
        )
        raise ValueError("No documentation exists in state to evaluate")

    evaluator_prompt = load_prompt("evaluation.md")

    evaluation_response = runtime.context.gateway.generate_structured_response(
        model=runtime.context.section_settings.evaluation_model,
        contents=[
            evaluator_prompt,
            json.dumps(state["data"]),
            state["generated_section_doc"],
            state["response_template"],
        ],
        schema_model=EvalResult,
        config=build_base_generation_config(),
    )

    issues = issues_from_eval_result(evaluation_response.content)

    # Update graph status with any resulting issues / clear issues if there are none
    emit_graph_status(
        name=state["section"].value,
        state=SectionState.EVALUATING,
        attempts=state["generation_attempts"],
        issues=issues,
        llm_response_metadata=evaluation_response.metadata,
    )

    logger.info(
        "graph.node.completed",
        node_name="evaluate_section_documentation",
        section=section,
        attempt=attempt,
        passed=evaluation_response.content.passed,
        issue_count=len(issues),
        blocking_issue_count=len(evaluation_response.content.blocking_issues),
        model_name=evaluation_response.metadata.model_name,
        elapsed_seconds=evaluation_response.metadata.elapsed_seconds,
        input_tokens=evaluation_response.metadata.input_tokens,
        output_tokens=evaluation_response.metadata.output_tokens,
        total_tokens=evaluation_response.metadata.total_tokens,
    )

    return {
        "evaluation_history": [evaluation_response.content],
        "llm_calls": [
            LLMCallEvent(
                node_name="evaluate_section_documentation",
                metadata=evaluation_response.metadata,
                section_subgraph=state["section"].value,
                section_attempt=state["generation_attempts"],
            )
        ],
    }


def _emit_section_documentation_generic(
    state: SectionDocumenterState,
    *,
    final_state: SectionState = SectionState.DONE,
    require_doc: bool = True,
    include_blocking_issues_header: bool = False,
) -> dict[str, Any]:
    """Format results of documentation into a state update to remerge back into the parent branch"""
    section = state["section"]
    section_name = section.value
    attempts = state.get("generation_attempts", 0)
    doc = state.get("generated_section_doc")

    logger.info(
        "graph.node.started",
        node_name="emit_section_documentation",
        section=section_name,
        attempts=attempts,
        final_state=final_state.value,
        require_doc=require_doc,
        include_blocking_issues_header=include_blocking_issues_header,
    )

    emit_graph_status(
        name=section.value,
        state=final_state,
        attempts=attempts,
    )

    if doc is None:
        if require_doc:
            logger.error(
                "graph.node.validation_failed",
                node_name="emit_section_documentation",
                section=section_name,
                attempts=attempts,
                final_state=final_state.value,
                missing_field="generated_section_doc",
            )
            raise ValueError(
                "Cannot emit section documentation because generated_section_doc is missing. "
                f"section={section.value}, attempts={attempts}, final_state={final_state}"
            )

        logger.info(
            "graph.node.skipped",
            node_name="emit_section_documentation",
            section=section_name,
            attempts=attempts,
            final_state=final_state.value,
            skip_reason="missing_doc_allowed",
        )

        return {
            "docs_by_section": {},
        }

    if include_blocking_issues_header:
        doc = prepend_unresolved_blocking_issues_warning_md(
            doc=doc,
            eval_result=get_latest_eval_result(state),
        )

    if final_state == SectionState.REACHED_RETRY_LIMIT:
        logger.warning(
            "graph.node.retry_limit_reached",
            node_name="emit_section_documentation",
            section=section_name,
            attempts=attempts,
            emitted_with_blocking_issues_header=include_blocking_issues_header,
        )

    logger.info(
        "graph.section.documentation.emitted",
        section=section_name,
        attempts=attempts,
        final_state=final_state.value,
        include_blocking_issues_header=include_blocking_issues_header,
    )

    logger.info(
        "graph.node.completed",
        node_name="emit_section_documentation",
        section=section_name,
        attempts=attempts,
        final_state=final_state.value,
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

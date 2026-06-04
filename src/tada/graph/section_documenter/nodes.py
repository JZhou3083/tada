import json
from typing import Any

import structlog
from langgraph.runtime import Runtime
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes

from tada.graph.ids import GraphName
from tada.graph.schemas import LLMCallRecord
from tada.graph.section_documenter.context import SectionDocumenterContext
from tada.graph.section_documenter.document_markdown import (
    prepend_unresolved_blocking_issues_warning_md,
)
from tada.graph.section_documenter.ids import SectionNodeId
from tada.graph.section_documenter.prompts import append_eval_feedback_prompt
from tada.graph.section_documenter.state import (
    SectionDocumenterInput,
    SectionDocumenterState,
    get_latest_eval_result,
    require_documentation_attempt,
    require_generated_section_doc,
)
from tada.graph.status import (
    IssueSeverity,
    SectionState,
    StatusIssue,
)
from tada.graph.status_stream import (
    StatusEmitRequest,
    emit_graph_status,
    issues_from_eval_result,
)
from tada.llm.configs import build_base_generation_config
from tada.llm.schemas import EvalResult
from tada.observability.otel.observe import observe
from tada.prompts import load_prompt

_GRAPH_NAME = GraphName.SECTION_DOCUMENTER.value

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__).bind(
    graph_name=_GRAPH_NAME
)


@observe(
    f"graph.node.{SectionNodeId.PREPARE_SECTION.value}",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
    },
)
def prepare_section(state: SectionDocumenterInput) -> dict[str, Any]:
    node_name = SectionNodeId.PREPARE_SECTION.value
    section_name = state["section"].value

    log = logger.bind(node_name=node_name, section_name=section_name)

    log.info(
        "graph.node.started",
    )
    # Skip all LLM generation - directly to emit - if payload is empty
    if not state.get("data"):
        emit_graph_status(
            StatusEmitRequest(
                graph_name=_GRAPH_NAME,
                section_name=state["section"].value,
                state=SectionState.SKIPPED,
                attempt=0,
                issues=(
                    StatusIssue(
                        "Generation skipped due to empty data payload.",
                        severity=IssueSeverity.INFO,
                        code="empty-payload",
                        source="graph",
                    ),
                ),
            )
        )

        log.info(
            "graph.node.skipped",
            skip_reason="empty_payload",
        )

        return {"skip_section": True}

    log.info(
        "graph.node.completed",
        skip_section=False,
    )

    return {"skip_section": False}


@observe(
    f"graph.node.{SectionNodeId.GENERATE_SECTION_DOCS.value}",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
    },
)
def generate_section_documentation(
    state: SectionDocumenterState, runtime: Runtime[SectionDocumenterContext]
) -> dict[str, Any]:
    node_name = SectionNodeId.GENERATE_SECTION_DOCS.value
    section_name = state["section"].value
    attempt = state.get("documentation_attempt", 0) + 1

    log = logger.bind(node_name=node_name, section_name=section_name, attempt=attempt)

    log.info("graph.node.started")

    emit_graph_status(
        StatusEmitRequest(
            graph_name=_GRAPH_NAME,
            section_name=state["section"].value,
            state=SectionState.GENERATING,
            attempt=attempt,
        )
    )

    full_prompt = state["prompt"]

    if "evaluation_history" in state:
        full_prompt = append_eval_feedback_prompt(
            full_prompt, state["evaluation_history"]
        )

    system_instruction = load_prompt("system.md")

    model_name = runtime.context.section_settings.documentation_model
    payload_json = json.dumps(
        state["data"],
        ensure_ascii=False,  # Prefer human and LLM-readable unicode over ascii
        sort_keys=True,  # Sort keys for reproducibility
    )

    try:
        response = runtime.context.gateway.generate_text(
            model=model_name,
            contents=[
                full_prompt,
                state["response_template"],
                payload_json,
            ],
            config=build_base_generation_config(
                system_instruction=system_instruction,
            ),
        )
    except Exception as exc:
        log.error(
            "graph.node.failed",
            failure_stage="llm_generation",
            model_name=model_name,
            exception_type=type(exc).__name__,
            exception_message=str(exc),
            payload_chars=len(payload_json),
            prompt_chars=len(full_prompt),
            response_template_chars=len(state["response_template"]),
            has_evaluation_history="evaluation_history" in state,
            exc_info=True,
        )

        emit_graph_status(
            StatusEmitRequest(
                graph_name=_GRAPH_NAME,
                section_name=state["section"].value,
                state=SectionState.FAILED,
                issues=(
                    StatusIssue(
                        message=str(exc),
                        severity=IssueSeverity.ERROR,
                        code=type(exc).__name__,
                        source="llm_gateway",
                    ),
                ),
            )
        )
        raise

    # Update the live token & cost tracking display
    emit_graph_status(
        StatusEmitRequest(
            graph_name=_GRAPH_NAME,
            section_name=state["section"].value,
            llm_response_metadata=response.metadata,
        )
    )

    log.info(
        "graph.node.completed",
        model_name=response.metadata.model_name,
        elapsed_seconds=response.metadata.elapsed_seconds,
        input_tokens=response.metadata.input_tokens,
        output_tokens=response.metadata.output_tokens,
        total_tokens=response.metadata.total_tokens,
    )

    return {
        "generated_section_doc": response.content,
        "documentation_attempt": attempt,
        "llm_calls": [
            LLMCallRecord(
                graph_name=_GRAPH_NAME,
                node_name=node_name,
                metadata=response.metadata,
                section_name=state["section"].value,
                attempt=attempt,
            )
        ],
    }


@observe(
    f"graph.node.{SectionNodeId.EVALUATE_SECTION_DOCS.value}",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
    },
)
def evaluate_section_documentation(
    state: SectionDocumenterState, runtime: Runtime[SectionDocumenterContext]
) -> dict[str, Any]:
    node_name = SectionNodeId.EVALUATE_SECTION_DOCS.value
    section_name = state["section"].value
    attempt = state.get("documentation_attempt")

    log = logger.bind(node_name=node_name, section_name=section_name, attempt=attempt)

    log.info("graph.node.started")

    emit_graph_status(
        StatusEmitRequest(
            graph_name=_GRAPH_NAME,
            section_name=state["section"].value,
            state=SectionState.EVALUATING,
            attempt=require_documentation_attempt(state),
        )
    )

    generated_doc = require_generated_section_doc(state)

    evaluator_prompt = load_prompt("evaluation.md")

    model_name = runtime.context.section_settings.evaluation_model
    payload_json = json.dumps(
        state["data"],
        ensure_ascii=False,
        sort_keys=True,
    )

    try:
        evaluation_response = runtime.context.gateway.generate_structured_response(
            model=model_name,
            contents=[
                evaluator_prompt,
                payload_json,
                generated_doc,
                state["response_template"],
            ],
            schema_model=EvalResult,
            config=build_base_generation_config(),
        )
    except Exception as exc:
        log.error(
            "graph.node.failed",
            failure_stage="llm_evaluation",
            model_name=model_name,
            exception_type=type(exc).__name__,
            exception_message=str(exc),
            payload_chars=len(payload_json),
            generated_doc_chars=len(generated_doc),
            response_template_chars=len(state["response_template"]),
            schema_model="EvalResult",
            exc_info=True,
        )

        emit_graph_status(
            StatusEmitRequest(
                graph_name=_GRAPH_NAME,
                section_name=state["section"].value,
                state=SectionState.FAILED,
                attempt=require_documentation_attempt(state),
                issues=(
                    StatusIssue(
                        message=str(exc),
                        severity=IssueSeverity.ERROR,
                        code=type(exc).__name__,
                        source="llm_gateway",
                    ),
                ),
            )
        )
        raise

    issues = issues_from_eval_result(evaluation_response.content)

    # Update graph status with any resulting issues / clear issues if there are none
    emit_graph_status(
        StatusEmitRequest(
            graph_name=_GRAPH_NAME,
            section_name=state["section"].value,
            state=SectionState.EVALUATING,
            attempt=require_documentation_attempt(state),
            issues=issues,
            llm_response_metadata=evaluation_response.metadata,
        )
    )

    log.info(
        "graph.node.completed",
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
            LLMCallRecord(
                graph_name=_GRAPH_NAME,
                node_name="evaluate_section_documentation",
                metadata=evaluation_response.metadata,
                section_name=state["section"].value,
                attempt=require_documentation_attempt(state),
            )
        ],
    }


def _emit_section_documentation_generic(
    state: SectionDocumenterState,
    *,
    node_id: SectionNodeId,
    final_state: SectionState,
    require_doc: bool = True,
    include_blocking_issues_header: bool = False,
) -> dict[str, Any]:
    """Format section documentation into a state update to remerge into the parent branch."""
    node_name = node_id.value
    section = state["section"]
    section_name = section.value
    attempt = require_documentation_attempt(state)

    log = logger.bind(node_name=node_name, section_name=section_name, attempt=attempt)

    doc = state.get("generated_section_doc")

    log.info(
        "graph.node.started",
        final_state=final_state.value,
        require_doc=require_doc,
        include_blocking_issues_header=include_blocking_issues_header,
    )

    emit_graph_status(
        StatusEmitRequest(
            graph_name=_GRAPH_NAME,
            section_name=section_name,
            state=final_state,
            attempt=attempt,
        )
    )

    if doc is None:
        if require_doc:
            log.error(
                "graph.node.validation_failed",
                final_state=final_state.value,
                missing_field="generated_section_doc",
            )
            raise ValueError(
                f"Cannot emit section documentation for section '{section_name}' as generated_section_doc is missing."
            )

        log.info(
            "graph.node.skipped",
            final_state=final_state.value,
            skip_reason="missing_doc_allowed",
        )

        return {
            "docs_by_section": {},
            "llm_calls": [],
        }

    if include_blocking_issues_header:
        doc = prepend_unresolved_blocking_issues_warning_md(
            doc=doc,
            eval_result=get_latest_eval_result(state),
        )

    if final_state == SectionState.REACHED_RETRY_LIMIT:
        log.warning(
            "graph.node.retry_limit_reached",
            emitted_with_blocking_issues_header=include_blocking_issues_header,
        )

    log.info(
        "graph.section.documentation.emitted",
        final_state=final_state.value,
        include_blocking_issues_header=include_blocking_issues_header,
    )

    log.info(
        "graph.node.completed",
        final_state=final_state.value,
    )

    return {"docs_by_section": {section: doc}, "llm_calls": []}


@observe(
    f"graph.node.{SectionNodeId.EMIT_SECTION_DOCS.value}",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
    },
)
def emit_section_documentation(state: SectionDocumenterState) -> dict[str, Any]:
    return _emit_section_documentation_generic(
        state,
        node_id=SectionNodeId.EMIT_SECTION_DOCS,
        final_state=SectionState.DONE,
    )


@observe(
    f"graph.node.{SectionNodeId.EMIT_SECTION_DOCS_AFTER_RETRY_LIMIT.value}",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
    },
)
def emit_section_documentation_retry_limit(
    state: SectionDocumenterState,
) -> dict[str, Any]:
    return _emit_section_documentation_generic(
        state,
        node_id=SectionNodeId.EMIT_SECTION_DOCS_AFTER_RETRY_LIMIT,
        final_state=SectionState.REACHED_RETRY_LIMIT,
        include_blocking_issues_header=True,
    )


@observe(
    f"graph.node.{SectionNodeId.EMIT_SECTION_DOCS_SKIPPED.value}",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
    },
)
def emit_section_documentation_skipped(state: SectionDocumenterState) -> dict[str, Any]:
    return _emit_section_documentation_generic(
        state,
        node_id=SectionNodeId.EMIT_SECTION_DOCS_SKIPPED,
        final_state=SectionState.SKIPPED,
        require_doc=False,
    )

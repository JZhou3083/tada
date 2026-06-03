from typing import Literal

import structlog
from langgraph.runtime import Runtime

from tada.graph.section_documenter.context import SectionDocumenterContext
from tada.graph.section_documenter.state import (
    SectionDocumenterState,
    get_latest_eval_result,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def route_after_precheck(state: SectionDocumenterState) -> Literal["skip", "generate"]:
    return "skip" if state.get("skip_section") else "generate"


def route_evaluation_results(
    state: SectionDocumenterState, runtime: Runtime[SectionDocumenterContext]
) -> Literal["emit", "emit_with_issues", "retry"]:
    latest_eval = get_latest_eval_result(state)
    if latest_eval is None:
        raise ValueError("No evaluation to route")

    section = state["section"].value
    attempt = state["generation_attempts"]
    blocking_issue_count = len(latest_eval.blocking_issues)
    non_blocking_issue_count = len(latest_eval.non_blocking_issues)

    if latest_eval.passed:
        logger.debug(
            "graph.edge.traversed",
            edge_name="route_evaluation_results",
            section=section,
            attempt=attempt,
            next_node="emit",
            non_blocking_issue_count=non_blocking_issue_count,
        )
        return "emit"

    elif (
        state["generation_attempts"]
        > runtime.context.section_settings.max_documentation_retries
    ):
        logger.debug(
            "graph.edge.traversed",
            edge_name="route_evaluation_results",
            section=section,
            attempt=attempt,
            max_documentation_retries=runtime.context.section_settings.max_documentation_retries,
            next_node="emit_with_issues",
            blocking_issue_count=blocking_issue_count,
            non_blocking_issue_count=non_blocking_issue_count,
        )
        return "emit_with_issues"

    logger.debug(
        "graph.edge.traversed",
        edge_name="route_evaluation_results",
        section=section,
        attempt=attempt,
        next_node="retry",
        blocking_issue_count=blocking_issue_count,
        non_blocking_issue_count=non_blocking_issue_count,
    )
    return "retry"

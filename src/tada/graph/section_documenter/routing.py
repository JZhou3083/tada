import logging
from typing import Literal

from tada.graph.config import MAX_SECTION_ATTEMPTS
from tada.graph.section_documenter.state import (
    SectionDocumenterState,
    get_latest_eval_result,
)

logger = logging.getLogger(__name__)


def route_after_precheck(state: SectionDocumenterState) -> Literal["skip", "generate"]:
    return "skip" if state.get("skip_section") else "generate"


def route_evaluation_results(
    state: SectionDocumenterState,
) -> Literal["emit", "emit_with_issues", "retry"]:
    latest_eval = get_latest_eval_result(state)
    if latest_eval is None:
        raise ValueError("No evaluation to route")

    if latest_eval.passed:
        logger.debug(
            "Emitting documentation for %s attempt=%d non_blocking_issues=%d",
            state["section"].value,
            state["generation_attempts"],
            len(latest_eval.non_blocking_issues),
        )
        return "emit"

    elif state["generation_attempts"] >= MAX_SECTION_ATTEMPTS:
        logger.debug(
            "Hit maximum attempts for %s attempt=%d blocking_issues=%d non_blocking_issues=%d",
            state["section"].value,
            state["generation_attempts"],
            len(latest_eval.blocking_issues),
            len(latest_eval.non_blocking_issues),
        )
        return "emit_with_issues"

    logger.debug(
        "Retrying documentation for %s attempt=%d blocking_issues=%d non_blocking_issues=%d",
        state["section"].value,
        state["generation_attempts"],
        len(latest_eval.blocking_issues),
        len(latest_eval.non_blocking_issues),
    )
    return "retry"

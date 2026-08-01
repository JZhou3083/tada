from typing import Callable, TypeVar

import structlog
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

F = TypeVar("F", bound=Callable)


# ------------------------
# Tenacity retries
# ------------------------


def log_retry(retry_state: RetryCallState) -> None:
    """Structured log emitted by tenacity before each sleep between retries."""
    # .outcome & .next_action are guaranteed at call time, but we guard in-line with type-checkers.
    exc = retry_state.outcome.exception() if retry_state.outcome is not None else None
    wait = (
        round(retry_state.next_action.sleep, 2)
        if retry_state.next_action is not None
        else None
    )
    logger.warning(
        "llm.request.retrying",
        attempt=retry_state.attempt_number,
        wait_seconds=wait,
        total_idle_seconds=round(retry_state.idle_for, 2),
        error_type=type(exc).__name__ if exc else None,
        error=str(exc) if exc else None,
    )


def with_retry(is_retryable: Callable[[BaseException], bool]) -> Callable[[F], F]:
    """Build a tenacity retry decorator using the shared rate-limit backoff policy.

    Every provider raises a different exception type for rate limiting, so each
    provider adapter defines its own `is_retryable_x_error` predicate and passes
    it here rather than sharing one exception check.
    """
    return retry(
        retry=retry_if_exception(is_retryable),
        wait=wait_exponential_jitter(initial=1, max=10, jitter=0.25),
        stop=stop_after_attempt(4),
        before_sleep=log_retry,
        reraise=True,
    )

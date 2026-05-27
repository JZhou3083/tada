import structlog
from google.genai.errors import APIError
from tenacity import (
    RetryCallState,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


# ------------------------
# Tenacity retries
# ------------------------


def _log_retry(retry_state: RetryCallState) -> None:
    """Structured log emitted by tenacity before each sleep between retries."""
    # .outcome & .next_action are guaranteed at call time, but we guard in-line with type-checkers.
    exc = retry_state.outcome.exception() if retry_state.outcome is not None else None
    wait = (
        round(retry_state.next_action.sleep, 2)
        if retry_state.next_action is not None
        else None
    )
    logger.warning(
        "genai.retry",
        attempt=retry_state.attempt_number,
        wait_seconds=wait,
        total_idle_seconds=round(retry_state.idle_for, 2),
        error_type=type(exc).__name__,
        error=str(exc),
    )


def _is_retryable_genai_error(exc: BaseException) -> bool:
    """Return whether a GenAI exception should be retried.

    Retries are limited to Google GenAI API errors with status code `429`, which
    indicates `RESOURCE_EXHAUSTED` / rate limiting.
    """
    if not isinstance(exc, APIError):
        return False

    code = getattr(exc, "code", None)
    return code == 429

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

from tada.trace_viewer._optional import require_module

logger = logging.getLogger(__name__)


class PhoenixError(RuntimeError):
    """Base class for Phoenix launch failures."""


class PhoenixLaunchError(PhoenixError):
    """Phoenix failed to launch."""


@dataclass(frozen=True)
class PhoenixSessionInfo:
    """Information about a running Phoenix session."""

    session: Any
    url: str | None


@contextmanager
def launch_phoenix(
    traces_df: Any,
    *,
    launch_kwargs: Mapping[str, Any] | None = None,
) -> Iterator[PhoenixSessionInfo]:
    """
    Launch a local Arize Phoenix app from an OpenInference traces DataFrame.

    Phoenix and pandas are optional dependencies, so they are imported lazily.
    """
    px = require_module("phoenix")

    kwargs = dict(launch_kwargs or {})

    try:
        trace_dataset = px.TraceDataset(traces_df)
        session = px.launch_app(trace=trace_dataset, **kwargs)
    except Exception as exc:
        raise PhoenixLaunchError(
            f"Failed to launch Phoenix trace viewer: {exc}"
        ) from exc

    url = _get_session_url(session)

    try:
        yield PhoenixSessionInfo(session=session, url=url)
    finally:
        close = getattr(session, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                logger.warning(
                    "Failed to close Phoenix session cleanly.", exc_info=True
                )


def _get_session_url(session: Any) -> str | None:
    for attr in ("url", "app_url", "base_url"):
        value = getattr(session, attr, None)
        if value:
            return str(value)

    view = getattr(session, "view", None)
    if callable(view):
        try:
            return str(view())
        except Exception:
            return None

    return None

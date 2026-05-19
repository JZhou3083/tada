# src/tada/observability/phoenix_launcher.py
from __future__ import annotations

import logging
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ------------------------
# Domain errors
# ------------------------


class PhoenixError(RuntimeError):
    """Base class for Phoenix launch failures."""


class PhoenixImportError(PhoenixError):
    """Phoenix is not installed or cannot be imported."""


class PhoenixLaunchError(PhoenixError):
    """Phoenix failed to launch."""


# ------------------------
# Structured results
# ------------------------


@dataclass(frozen=True)
class PhoenixSessionInfo:
    """Small wrapper to return the session and URL in a stable shape."""

    session: Any
    url: str


# ------------------------
# Internal warning suppression
# ------------------------


def silence_phoenix_noise() -> None:
    """
    Suppress known noisy warnings during Phoenix startup.
    Keep this minimal and well-scoped.
    """
    # Your CLI currently silences SAWarning about expression-based indexes. 【1-abd929】
    try:
        from sqlalchemy.exc import SAWarning
    except Exception:
        SAWarning = Warning  # fallback; safe but less specific

    warnings.filterwarnings(
        "ignore",
        message=r".*Skipped unsupported reflection of expression-based index.*",
        category=SAWarning,
    )


# ------------------------
# API
# ------------------------


@contextmanager
def launch_phoenix(
    traces_df: pd.DataFrame,
    *,
    suppress_warnings: bool = True,
    launch_kwargs: Optional[Dict[str, Any]] = None,
) -> Iterator[PhoenixSessionInfo]:
    """
    Launch an Arize Phoenix session from a traces dataframe and ensure cleanup.

    - No printing, no sleeping, no CLI exits.
    - Caller handles UX and process lifetime.
    - Always ends the session on exit if it was created.

    Raises:
      - PhoenixImportError
      - PhoenixLaunchError
    """
    if traces_df is None or traces_df.empty:
        raise PhoenixLaunchError("Cannot launch Phoenix: traces_df is empty.")

    if suppress_warnings:
        silence_phoenix_noise()

    launch_kwargs = launch_kwargs or {}

    session = None
    try:
        try:
            import phoenix as px  # type: ignore
        except Exception as exc:
            raise PhoenixImportError(
                "Phoenix could not be imported. Ensure 'arize-phoenix' is installed."
            ) from exc

        # Construct dataset and launch
        trace_dataset = px.TraceDataset(traces_df)
        session = px.launch_app(trace=trace_dataset, **launch_kwargs)

        # Some phoenix session objects have `.url`; keep it defensive.
        url = getattr(session, "url", "") or ""
        yield PhoenixSessionInfo(session=session, url=url)

    except PhoenixError:
        # Preserve our typed exceptions
        raise
    except Exception as exc:
        raise PhoenixLaunchError(f"{type(exc).__name__}: {exc}") from exc
    finally:
        # Best-effort shutdown
        if session is not None:
            try:
                session.end()
            except Exception as exc:
                logger.warning("Failed to end Phoenix session cleanly: %s", exc)

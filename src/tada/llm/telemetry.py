import logging

from google.genai import types


def log_genai_usage(
    logger: logging.Logger,
    response: types.GenerateContentResponse,
    *,
    label: str,
    elapsed: float,
    model: str | None = None,
):
    um = getattr(response, "usage_metadata", None)
    text = getattr(response, "text", "") or ""
    chars = len(str(text))

    um = getattr(response, "usage_metadata", None)
    logger.debug(
        "Generation completed label=%s model=%s duration=%.3fs chars=%d tokens_total=%s "
        "tokens_prompt=%s tokens_output=%s tokens_cached=%s cache_hit=%s",
        label,
        model or "-",
        elapsed,
        chars,
        getattr(um, "total_token_count", None),
        getattr(um, "prompt_token_count", None),
        getattr(um, "candidates_token_count", None),
        getattr(um, "cached_content_token_count", None),
        bool(getattr(um, "cached_content_token_count", 0) or 0),
    )

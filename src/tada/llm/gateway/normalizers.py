from typing import Sequence

from google.genai import types
from pydantic import BaseModel

# ------------------------
# Contents handling
# ------------------------


def _contents_from_text_parts(text_parts: Sequence[str]) -> types.Content:
    """Create a user content object from one or more text parts.

    Args:
        text_parts: Non-empty sequence of text strings to send as user input.

    Returns:
        A Google GenAI `Content` object with role set to `"user"`.

    Raises:
        ValueError: If `text_parts` is empty or contains empty strings.
    """
    if not text_parts:
        raise ValueError("text_parts must contain at least one string")

    empty_indexes = [idx for idx, part in enumerate(text_parts) if not part.strip()]
    if empty_indexes:
        raise ValueError(
            "text_parts must not contain empty or whitespace-only strings; "
            f"invalid indexes: {empty_indexes}"
        )

    return types.Content(
        role="user",
        parts=[types.Part.from_text(text=part) for part in text_parts],
    )


def _normalize_contents(
    contents: types.ContentListUnionDict | Sequence[str] | str,
) -> types.ContentListUnionDict:
    """Normalise supported prompt inputs into Google GenAI content format.

    Supported inputs:
    - `str`: converted into a single user text part
    - `Sequence[str]`: converted into multiple user text parts
    - Google GenAI content object/dict: returned unchanged

    Args:
        contents: Prompt content in one of the supported formats.

    Returns:
        A value suitable for `client.models.generate_content(contents=...)`.

    Raises:
        TypeError: If a sequence contains non-string values.
        ValueError: If a string or string sequence is empty.
    """
    if isinstance(contents, str):
        if not contents.strip():
            raise ValueError("contents must not be an empty or whitespace-only string")

        return _contents_from_text_parts([contents])

    if isinstance(contents, Sequence) and not isinstance(contents, (str, bytes)):
        non_string_items = [
            (idx, type(part).__name__)
            for idx, part in enumerate(contents)
            if not isinstance(part, str)
        ]

        if non_string_items:
            raise TypeError(
                "contents must be a string, a sequence of strings, "
                "or a valid Google GenAI contents object. "
                f"Found non-string sequence items: {non_string_items}"
            )

        return _contents_from_text_parts(contents)

    return contents


# ------------------------
# Config handling
# ------------------------


def _coerce_config(
    config: types.GenerateContentConfigOrDict,
) -> types.GenerateContentConfig:
    """Convert a config dict into a `GenerateContentConfig` instance if needed.

    Args:
        config: Existing GenAI config object or compatible dictionary.

    Returns:
        A validated `GenerateContentConfig` instance.

    Raises:
        ValidationError: If a dictionary config is not valid.
    """
    if isinstance(config, types.GenerateContentConfig):
        return config

    return types.GenerateContentConfig.model_validate(config)


def _validate_schema_model(schema_model: object) -> None:
    """Validate that an object is a Pydantic model class.

    Args:
        schema_model: Object expected to be a subclass of `pydantic.BaseModel`.

    Raises:
        TypeError: If `schema_model` is not a class, or if it is not a subclass
            of `pydantic.BaseModel`.
    """
    if not isinstance(schema_model, type) or not issubclass(schema_model, BaseModel):
        raise TypeError(
            "schema_model must be a subclass of pydantic.BaseModel, "
            f"got {schema_model!r} (type={type(schema_model).__name__})"
        )


def _resolve_structured_config(
    schema_model: type[BaseModel],
    config: types.GenerateContentConfigOrDict | None,
) -> types.GenerateContentConfig:
    """Create a generation config for structured JSON responses.

    The returned config requests a JSON response and applies the JSON schema
    generated from the provided Pydantic model.

    Args:
        schema_model: Pydantic `BaseModel` subclass defining the expected response schema.
        config: Optional base Google GenAI generation config or compatible dictionary.

    Returns:
        A `GenerateContentConfig` configured for JSON structured output.

    Raises:
        ValidationError: If `config` is a dictionary that cannot be validated as a
            `GenerateContentConfig`.
    """
    base_config = (
        types.GenerateContentConfig() if config is None else _coerce_config(config)
    )

    return base_config.model_copy(
        update={
            "response_mime_type": "application/json",
            "response_json_schema": schema_model.model_json_schema(),
        }
    )

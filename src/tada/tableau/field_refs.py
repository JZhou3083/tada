from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

# Matches Tableau-style bracket tokens: [Something], including spaces inside brackets.
BRACKET_TOKEN_RE = re.compile(r"\[\s*([^\]]+?)\s*\]")

# Strips Tableau-generated suffixes like "Field_123456" -> "Field"
TRAILING_ID_RE = re.compile(r"^(.+?)_\d{6,}$")


def parse_field_ref(ref: str) -> list[str]:
    """
    Parse a Tableau field reference of the form "[x].[y].[z]" into its parts.

    Returns:
        A list of parts without surrounding brackets, or [] if `ref` is not in the
        expected bracketed Tableau format.
    """
    if not (ref.startswith("[") and ref.endswith("]")):
        return []

    # Remove outer brackets and split on "].[" boundaries.
    inner = ref[1:-1]
    parts = [p.strip() for p in inner.split("].[")]
    return parts if all(parts) else []


def field_key_from_ref(ref: str, *, keep_prefix: bool = False) -> str:
    """
    Derive a lookup key from a Tableau field reference.

    Args:
        ref: Tableau field reference like "[ds].[field]" or "[field]".
        keep_prefix: If True, keep the full "x].[y" chain; otherwise return the last part.

    Returns:
        The derived key ("" if `ref` is not a Tableau-style field reference).
    """
    parts = parse_field_ref(ref)
    if not parts:
        return ""
    return "].[".join(parts) if keep_prefix else parts[-1]


def _columns_mapping(obj: object) -> Mapping[str, Any]:
    """
    Normalise inputs to a mapping that looks like { "[Field]": {..col..}, ... }.

    Accepts either:
    - a dict containing {"columns": {...}}
    - a dict whose keys already look like bracketed Tableau fields.

    Returns:
        A mapping of column-name -> column-metadata, or {} if not recognised.
    """
    if not isinstance(obj, Mapping):
        return {}

    columns = obj.get("columns")
    if isinstance(columns, Mapping):
        return columns

    # Heuristic: treat obj itself as the columns mapping if its keys look bracketed.
    if obj and all(
        isinstance(k, str) and k.startswith("[") and k.endswith("]") for k in obj.keys()
    ):
        return obj

    return {}


def strip_generated_suffix(name: str) -> str:
    """
    Remove Tableau-style generated suffixes like '_123456' from a field name.
    """
    return TRAILING_ID_RE.sub(r"\1", name)


def build_field_map(obj: object, *, keep_prefix: bool = False) -> dict[str, str]:
    """
    Build a mapping from internal Tableau field keys to human-friendly captions.

    The input can be a datasource dict containing a "columns" dict, or the "columns"
    dict itself.

    Strategy:
    - Key: derived from the column name using `field_key_from_ref(...)`.
    - Value: column["caption"] if present; otherwise a fallback derived from the key
      (with Tableau-generated suffix removed).

    Args:
        obj: Datasource dict or columns dict.
        keep_prefix: Whether to keep the full prefix chain in derived keys.

    Returns:
        Dict mapping internal field key -> caption/fallback.
    """
    cols = _columns_mapping(obj)
    field_map: dict[str, str] = {}

    for name_str, col in cols.items():
        key = field_key_from_ref(name_str, keep_prefix=keep_prefix)
        if not key:
            continue

        caption = ""
        if isinstance(col, Mapping):
            raw = col.get("caption")
            caption = raw.strip() if isinstance(raw, str) else ""

        if caption:
            field_map[key] = caption
        else:
            # Don't overwrite a real caption discovered earlier.
            field_map.setdefault(key, strip_generated_suffix(key))

    return field_map


def replace_values(
    obj: object,
    field_map: Mapping[str, str],
    *,
    skip_keys: set[str] | frozenset[str] = frozenset(),
) -> object:
    """
    Recursively apply Tableau field-name resolution to a nested structure.

    Behaviour:
    - Dict keys that look like bracketed field refs are renamed when their inner key
      exists in `field_map`.
    - String values: replace any bracket tokens "[...]" using `field_map` (token inner text
      is the lookup key).
    - Values under keys listed in `skip_keys` are not modified if they are strings.

    Args:
        obj: Arbitrary nested structure (dict/list/str/other).
        field_map: Mapping of internal keys -> captions.
        skip_keys: Dict keys whose string values should be left unchanged.

    Returns:
        A transformed structure with replacements applied.
    """
    if isinstance(obj, Mapping):
        new: dict[Any, Any] = {}
        for k, v in obj.items():
            new_key = _rename_key(k, field_map)

            # Preserve string values under specific keys (based on original key name).
            if isinstance(k, str) and k in skip_keys and isinstance(v, str):
                new[new_key] = v
            else:
                new[new_key] = replace_values(v, field_map, skip_keys=skip_keys)
        return new

    if isinstance(obj, list):
        return [replace_values(x, field_map, skip_keys=skip_keys) for x in obj]

    if isinstance(obj, str):
        return BRACKET_TOKEN_RE.sub(
            lambda m: f"[{field_map.get(m.group(1).strip(), m.group(1).strip())}]", obj
        )

    return obj


def _rename_key(key: Any, field_map: Mapping[str, str]) -> Any:
    """
    Rename dict keys that look like Tableau field refs.

    Keeps the key shape bracketed if it was bracketed originally.
    """
    if not isinstance(key, str):
        return key

    stripped = key.strip()
    is_bracketed = stripped.startswith("[") and stripped.endswith("]")

    inner = stripped.strip("[] ").strip()
    if inner in field_map:
        return f"[{field_map[inner]}]" if is_bracketed else field_map[inner]

    # Preserve original bracketed formatting if it looks like a field ref.
    return f"[{inner}]" if is_bracketed else key

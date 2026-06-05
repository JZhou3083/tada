from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


def normalise_llm_payload(value: Any) -> Any:
    """Convert workbook metadata into deterministic JSON-serialisable values."""
    if value is None or isinstance(value, str | int | float | bool):
        return value

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, datetime | date):
        return value.isoformat()

    if isinstance(value, Enum):
        return value.value

    if is_dataclass(value) and not isinstance(value, type):
        return normalise_llm_payload(asdict(value))

    if isinstance(value, dict):
        return {str(key): normalise_llm_payload(item) for key, item in value.items()}

    if isinstance(value, list | tuple):
        return [normalise_llm_payload(item) for item in value]

    if isinstance(value, set | frozenset):
        return sorted(normalise_llm_payload(item) for item in value)

    raise TypeError(f"Unsupported LLM payload value type: {type(value).__name__}")

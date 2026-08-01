from typing import Any, Protocol, Sequence, TypeVar

import structlog
from pydantic import BaseModel, ValidationError

from tada.llm.configs import GenerationConfig
from tada.llm.gateway.types import GatewayResponse

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

ContentsInput = str | Sequence[str]

T = TypeVar("T", bound=BaseModel)


class LLMGateway(Protocol):
    """Provider-neutral interface implemented by every provider adapter.

    Graph nodes only ever call these two methods on `runtime.context.gateway`,
    so this is the entire surface a new provider adapter must implement.
    """

    def generate_text(
        self,
        *,
        model: str,
        contents: ContentsInput,
        config: GenerationConfig | None = None,
    ) -> GatewayResponse[str]: ...

    def generate_structured_response(
        self,
        *,
        model: str,
        contents: ContentsInput,
        schema_model: type[T],
        config: GenerationConfig | None = None,
    ) -> GatewayResponse[T]: ...


def validate_schema_model(schema_model: object) -> None:
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


def validate_structured_payload(
    payload: dict[str, Any],
    schema_model: type[T],
    *,
    request_id: str,
) -> T:
    """Validate a parsed JSON payload against a Pydantic schema.

    Every provider adapter's `generate_structured_response` gets the model to
    produce a JSON object by whatever means that provider supports (JSON mode,
    a JSON-schema-constrained response, or forced tool-use), parses it into a
    plain `dict`, then calls this to do the actual schema validation.

    Args:
        payload: Parsed JSON response content.
        schema_model: Pydantic `BaseModel` subclass defining the expected schema.
        request_id: Correlation ID for the originating request, for logging.

    Returns:
        A validated instance of `schema_model`.

    Raises:
        ValueError: If `payload` does not match `schema_model`.
    """
    try:
        return schema_model.model_validate(payload)
    except ValidationError as exc:
        logger.error(
            "llm.structured.validation_failed",
            request_id=request_id,
            schema=schema_model.__name__,
            error_type=type(exc).__name__,
            error=str(exc),
            payload_preview=str(payload)[:250],
        )
        raise ValueError(
            "Model returned JSON that does not match the expected schema "
            f"{schema_model.__name__}. Validation error: {exc}"
        ) from exc

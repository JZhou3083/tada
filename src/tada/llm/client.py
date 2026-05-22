from functools import lru_cache
from typing import Sequence, TypeVar

from google.genai import Client, types
from pydantic import BaseModel, ValidationError

# TODO: add 429 retries to the gateway
# TODO: add logging to the gateway

T = TypeVar("T", bound=BaseModel)


class VertexAIGateway:
    """Small gateway around the Google GenAI client.

    Provides convenience methods for generating plain text and structured responses.
    """

    def __init__(self, client: Client):
        self.client = client

    @staticmethod
    def contents_from_text_parts(text_parts: Sequence[str]) -> types.Content:
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

    @staticmethod
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
                raise ValueError(
                    "contents must not be an empty or whitespace-only string"
                )

            return VertexAIGateway.contents_from_text_parts([contents])

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

            return VertexAIGateway.contents_from_text_parts(contents)

        return contents

    def generate_text(
        self,
        *,
        model: str,
        contents: types.ContentListUnionDict | Sequence[str] | str,
        config: types.GenerateContentConfigOrDict | None = None,
    ) -> tuple[types.GenerateContentResponse, str]:
        """Generate a plain text response from a model.

        Args:
            model: Model name or ID to use.
            contents: Prompt content as a string, sequence of strings, or GenAI content object.
            config: Optional Google GenAI generation config.

        Returns:
            Tuple of the raw GenAI response and extracted response text.

        Raises:
            ValueError: If the model returns no text.
            TypeError: If `contents` is not in a supported format.
        """
        response = self.client.models.generate_content(
            model=model,
            contents=self._normalize_contents(contents),
            config=config,
        )

        if response.text is None:
            raise ValueError(
                "Model returned no text response. "
                "Check whether the response was blocked, empty, or returned only non-text parts."
            )

        return response, response.text

    @staticmethod
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

    @staticmethod
    def _validate_schema_model(schema_model: object) -> None:
        """Validate that an object is a Pydantic model class.

        Args:
            schema_model: Object expected to be a subclass of `pydantic.BaseModel`.

        Raises:
            TypeError: If `schema_model` is not a class, or if it is not a subclass
                of `pydantic.BaseModel`.
        """
        if not isinstance(schema_model, type) or not issubclass(
            schema_model, BaseModel
        ):
            raise TypeError(
                "schema_model must be a subclass of pydantic.BaseModel, "
                f"got {schema_model!r} (type={type(schema_model).__name__})"
            )

    def _resolve_structured_config(
        self,
        *,
        schema_model: type[BaseModel],
        config: types.GenerateContentConfigOrDict | None,
    ) -> types.GenerateContentConfig:
        """Create a generation config for JSON structured output.

        Adds:
        - `response_mime_type="application/json"`
        - `response_json_schema` from the provided Pydantic model

        Args:
            schema_model: Pydantic model used to define the expected response schema.
            config: Optional base GenAI generation config.

        Returns:
            A config object configured for JSON schema output.
        """
        base_config = (
            types.GenerateContentConfig()
            if config is None
            else self._coerce_config(config)
        )

        return base_config.model_copy(
            update={
                "response_mime_type": "application/json",
                "response_json_schema": schema_model.model_json_schema(),
            }
        )

    def generate_structured_response(
        self,
        *,
        model: str,
        contents: types.ContentListUnionDict | Sequence[str] | str,
        schema_model: type[T],
        config: types.GenerateContentConfigOrDict | None = None,
    ) -> tuple[types.GenerateContentResponse, T]:
        """Generate and validate a structured response using a Pydantic model.

        The model response is requested as JSON using the schema generated from
        `schema_model`, then validated into an instance of that model.

        Args:
            model: Model name or ID to use.
            contents: Prompt content as a string, sequence of strings, or GenAI content object.
            schema_model: Pydantic `BaseModel` subclass defining the expected JSON response.
            config: Optional Google GenAI generation config.

        Returns:
            Tuple of the raw GenAI response and validated Pydantic model instance.

        Raises:
            TypeError: If `schema_model` is not a Pydantic `BaseModel` subclass, or if
                `contents` is not in a supported format.
            ValueError: If the model returns no text, invalid JSON, or JSON that does not
                match `schema_model`.
            ValidationError: If `config` is invalid.
        """
        self._validate_schema_model(schema_model)

        resolved_config = self._resolve_structured_config(
            schema_model=schema_model,
            config=config,
        )

        response, response_text = self.generate_text(
            model=model,
            contents=contents,
            config=resolved_config,
        )

        try:
            response_obj = schema_model.model_validate_json(response_text)
        except ValidationError as exc:
            raise ValueError(
                "Model returned JSON that does not match the expected schema "
                f"{schema_model.__name__}. Validation error: {exc}"
            ) from exc
        except ValueError as exc:
            raise ValueError(
                "Model returned invalid JSON for expected schema "
                f"{schema_model.__name__}. Response text starts with: "
                f"{response_text[:250]!r}"
            ) from exc

        return response, response_obj


@lru_cache(maxsize=1)
def get_genai_client() -> Client:
    return Client(
        vertexai=True,
        project="jlr-dl-cat",
        location="global",
    )


@lru_cache(maxsize=1)
def get_vertexai_gateway() -> VertexAIGateway:
    return VertexAIGateway(get_genai_client())

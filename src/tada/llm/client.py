from functools import lru_cache
from typing import TypeVar

from google.genai import Client, types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class VertexAIGateway:
    def __init__(self, client: Client):
        self.client = client

    def generate_text(
        self,
        *,
        model: str,
        contents: types.ContentListUnionDict,
        config: types.GenerateContentConfigOrDict | None = None,
    ) -> tuple[types.GenerateContentResponse, str]:
        response = self.client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        if response.text is None:
            raise ValueError("Model returned no text response")

        return response, response.text

    def _coerce_config(
        self,
        config: types.GenerateContentConfigOrDict,
    ) -> types.GenerateContentConfig:
        if isinstance(config, types.GenerateContentConfig):
            return config

        return types.GenerateContentConfig.model_validate(config)

    def _resolve_structured_config(
        self,
        *,
        schema_model: type[BaseModel],
        config: types.GenerateContentConfigOrDict | None,
    ) -> types.GenerateContentConfig:
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
        contents: types.ContentListUnionDict,
        schema_model: type[T],
        config: types.GenerateContentConfigOrDict | None = None,
    ) -> tuple[types.GenerateContentResponse, T]:
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
        except Exception as exc:
            raise ValueError(
                f"Model returned invalid structured JSON for {schema_model.__name__}"
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

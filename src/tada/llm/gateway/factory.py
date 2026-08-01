from functools import lru_cache

from tada.llm.gateway.base import LLMGateway
from tada.llm.gateway.providers.anthropic import get_anthropic_gateway
from tada.llm.gateway.providers.google_vertex import get_google_vertex_gateway
from tada.llm.gateway.providers.openai_compatible import (
    get_deepseek_gateway,
    get_openai_gateway,
)
from tada.settings import LLMProvider, get_settings


@lru_cache(maxsize=1)
def get_gateway() -> LLMGateway:
    """Build (and cache) the `LLMGateway` selected by `TADA_LLM_PROVIDER`."""
    settings = get_settings()

    match settings.llm_provider:
        case LLMProvider.GOOGLE_VERTEX:
            return get_google_vertex_gateway(
                settings.client_project, settings.client_location
            )
        case LLMProvider.OPENAI:
            if settings.openai_api_key is None:
                raise ValueError(
                    "TADA_OPENAI_API_KEY must be set when TADA_LLM_PROVIDER=openai."
                )
            return get_openai_gateway(settings.openai_api_key.get_secret_value())
        case LLMProvider.ANTHROPIC:
            if settings.anthropic_api_key is None:
                raise ValueError(
                    "TADA_ANTHROPIC_API_KEY must be set when TADA_LLM_PROVIDER=anthropic."
                )
            return get_anthropic_gateway(settings.anthropic_api_key.get_secret_value())
        case LLMProvider.DEEPSEEK:
            if settings.deepseek_api_key is None:
                raise ValueError(
                    "TADA_DEEPSEEK_API_KEY must be set when TADA_LLM_PROVIDER=deepseek."
                )
            return get_deepseek_gateway(
                settings.deepseek_api_key.get_secret_value(),
                settings.deepseek_base_url,
            )

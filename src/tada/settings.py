from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from platformdirs import user_state_dir
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from tada.graph.section_documenter.settings import SectionDocumenterSettings
from tada.graph.workbook_documenter.settings import WorkbookDocumenterSettings


class LLMProvider(StrEnum):
    GOOGLE_VERTEX = "google_vertex"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


class GraphSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    section_documenter: SectionDocumenterSettings = Field(
        default_factory=SectionDocumenterSettings
    )
    workbook_documenter: WorkbookDocumenterSettings = Field(
        default_factory=WorkbookDocumenterSettings
    )


class TadaSettings(BaseSettings):
    """
    Application settings for TaDA.

    Settings are automatically loaded from environment variables and an optional `.env` file.
    All variables are expected to be prefixed with 'TADA_'.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TADA_",  # Automatically prefixes all fields
        env_nested_delimiter="__",  # Enables e.g. TADA_GRAPH__SECTION_DOCUMENTER__DOCUMENTATION_MODEL
        extra="ignore",
    )

    state_dir: Path = Field(
        default=Path(user_state_dir("tada", appauthor=False)),
        description=(
            "Directory used for local runtime state such as traces, checkpoints and metadata."
        ),
    )
    client_project: str = Field(
        default="jlr-dl-cat",
        description=(
            "The Google Cloud project ID used to initialize the GenAI SDK client. "
            "Defaults to 'jlr-dl-cat'."
        ),
    )
    client_location: str = Field(
        default="global",
        description=(
            "The Google Cloud region/location (e.g., 'us-central1') used for the GenAI SDK client. "
            "Defaults to 'global'."
        ),
    )

    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="Which LLM backend to use for all graph generation calls.",
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        description="API key used when `llm_provider` is 'openai'.",
    )
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        description="API key used when `llm_provider` is 'anthropic'.",
    )
    deepseek_api_key: SecretStr | None = Field(
        default=None,
        description="API key used when `llm_provider` is 'deepseek'.",
    )
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        description="Base URL for the DeepSeek OpenAI-compatible API.",
    )

    graph: GraphSettings = Field(default_factory=GraphSettings)

    @field_validator("state_dir")
    @classmethod
    def expand_runtime_dir(cls, value: Path) -> Path:
        """
        Return `state_dir` as a consistent absolute path.

        This allows users to provide values such as `~/.tada`, `./.tada`, or
        another relative path via `TADA_STATE_DIR`, while ensuring the rest of
        the application receives an expanded, resolved path.
        """
        return value.expanduser().resolve()


@lru_cache(maxsize=1)
def get_settings() -> TadaSettings:
    return TadaSettings(
        **{}  # Empty dict unpacking silences pylance error for fields injected at runtime
    )

from functools import lru_cache
from pathlib import Path

from platformdirs import user_state_dir
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TadaSettings(BaseSettings):
    """
    Application settings for TaDA.

    Settings are automatically loaded from environment variables and an optional `.env` file.
    All variables are expected to be prefixed with 'TADA_'.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TADA_",  # Automatically prefixes all fields
        extra="ignore",
    )

    state_dir: Path = Field(
        default=Path(user_state_dir("tada", appauthor=False)),
        description=(
            "Directory used for local runtime state such as traces, checkpoints and metadata."
        ),
    )
    client_project: str = Field(
        validation_alias="TADA_CLIENT_PROJECT",
        description=(
            "The Google Cloud project ID used to initialize the GenAI SDK client."
        ),
    )
    client_location: str = Field(
        description=(
            "The Google Cloud region/location (e.g., 'us-central1') used for the GenAI SDK client."
        ),
    )

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

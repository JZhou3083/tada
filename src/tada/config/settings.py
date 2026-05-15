from pathlib import Path

from platformdirs import user_state_dir
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TadaSettings(BaseSettings):
    """
    Application settings for TaDA.

    Settings are loaded from environment variables and an optional `.env` file.
    Unknown settings are ignored.

    `state_dir` controls where local runtime state is stored, including traces,
    checkpoints, run metadata, and other non-user-facing execution artefacts.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    state_dir: Path = Field(
        default=Path(user_state_dir("tada", appauthor=False)),
        validation_alias="TADA_STATE_DIR",
        description=(
            "Directory used for local runtime state such as traces, checkpoints "
            "and run metadata. Can be overridden with TADA_STATE_DIR. Defaults "
            "to the platform-specific user state directory."
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

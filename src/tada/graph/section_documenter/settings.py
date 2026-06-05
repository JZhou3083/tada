from pydantic import BaseModel, ConfigDict, Field


class SectionDocumenterSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    documentation_model: str = Field(
        default="gemini-3-flash-preview",
        description="Model used to generate section documentation.",
    )
    evaluation_model: str = Field(
        default="gemini-3-flash-preview",
        description="Model used to evaluate generated section documentation.",
    )
    max_documentation_retries: int = Field(
        default=2,
        ge=0,
        le=4,  # Reasonable top-limit for retries
        description=(
            "Maximum number of retries after the initial documentation attempt. "
            "A value of 2 allows up to 3 total generation attempts."
        ),
    )

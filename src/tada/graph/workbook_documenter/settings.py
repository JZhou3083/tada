from pydantic import BaseModel, ConfigDict, Field


class WorkbookDocumenterSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary_model: str = Field(
        default="gemini-3-flash-preview",
        description="Model used to generate the workbook-level summary.",
    )

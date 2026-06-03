from dataclasses import dataclass


@dataclass(frozen=True)
class WorkbookDocumenterSettings:
    summary_model: str


# TODO: move settings configuration to pydantic-settings
def default_workbook_documenter_settings() -> WorkbookDocumenterSettings:
    return WorkbookDocumenterSettings(
        summary_model="gemini-3-flash-preview",
    )

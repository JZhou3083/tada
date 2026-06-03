from dataclasses import dataclass


@dataclass(frozen=True)
class SectionDocumenterSettings:
    documentation_model: str
    evaluation_model: str
    max_documentation_retries: int


def default_section_documenter_settings() -> SectionDocumenterSettings:
    return SectionDocumenterSettings(
        documentation_model="gemini-3-flash-preview",
        evaluation_model="gemini-3-flash-preview",
        max_documentation_retries=2,
    )

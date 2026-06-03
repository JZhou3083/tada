from dataclasses import dataclass


@dataclass(frozen=True)
class SectionDocumenterSettings:
    generation_model: str
    evaluation_model: str
    max_section_attempts: int


def default_section_documenter_settings() -> SectionDocumenterSettings:
    return SectionDocumenterSettings(
        generation_model="gemini-...",
        evaluation_model="gemini-...",
        max_section_attempts=3,
    )

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GenerationConfig:
    """Provider-neutral generation parameters.

    Each provider adapter is responsible for translating this into its own
    SDK's request shape (e.g. Google's `GenerateContentConfig`, OpenAI's
    `chat.completions.create(...)` kwargs, Anthropic's `messages.create(...)`
    kwargs).
    """

    system_instruction: str | None = None
    temperature: float = 0.2
    top_p: float = 0.2
    seed: int = 101
    max_output_tokens: int = 8192
    labels: dict[str, str] = field(default_factory=dict)


def build_base_generation_config(
    *,
    system_instruction: str | None = None,
    labels: dict[str, str] | None = None,
) -> GenerationConfig:
    return GenerationConfig(
        system_instruction=system_instruction,
        labels={
            "project": "TADA",
            "workbook": labels.get("workbook", "") if labels else "",
            "sections": labels.get("sections", "") if labels else "",
            "env": labels.get("env", "") if labels else "",
        },
    )

from google.genai import types


def build_base_generation_config(
    *, system_instruction: str | None = None
) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.2,
        top_p=0.2,
        seed=101,
        candidate_count=1,
        thinking_config=types.ThinkingConfig(
            include_thoughts=False, thinking_level=types.ThinkingLevel.LOW
        ),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

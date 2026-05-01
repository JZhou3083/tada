# from importlib import resources
#     # sys_instruction = (resources.files("tada") / "prompts" / "system.md").read_text(
#     #     encoding="utf-8"
#     # )

from google.genai import types


def build_text_generation_config(
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


def build_json_generation_config(json_schema: dict) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        temperature=0.2,
        top_p=0.2,
        seed=101,
        candidate_count=1,
        thinking_config=types.ThinkingConfig(
            include_thoughts=False, thinking_level=types.ThinkingLevel.LOW
        ),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        response_mime_type="application/json",
        response_json_schema=json_schema,
    )

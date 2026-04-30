from functools import lru_cache
from importlib import resources

from google.genai import Client, types


@lru_cache(maxsize=1)
def get_genai_client():
    return Client(
        vertexai=True,
        project="jlr-dl-cat",
        location="global",
    )


def get_section_summary_generation_config() -> types.GenerateContentConfig:
    sys_instruction = (resources.files("tada") / "prompts" / "system.md").read_text(
        encoding="utf-8"
    )
    return types.GenerateContentConfig(
        system_instruction=sys_instruction,
        temperature=0.2,
        top_p=0.2,
        seed=101,
        candidate_count=1,
        thinking_config=types.ThinkingConfig(
            include_thoughts=False, thinking_level=types.ThinkingLevel.LOW
        ),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def get_compiled_doc_generation_config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        temperature=0.2,
        top_p=0.2,
        seed=101,
        candidate_count=1,
        thinking_config=types.ThinkingConfig(
            include_thoughts=False, thinking_level=types.ThinkingLevel.LOW
        ),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

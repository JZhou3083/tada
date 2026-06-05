import pytest

from tada.prompts.loader import load_prompt


@pytest.fixture(autouse=True)
def clear_section_prompt_cache():
    load_prompt.cache_clear()
    yield
    load_prompt.cache_clear()


@pytest.mark.parametrize("file", ("evaluation.md", "summariser.md", "system.md"))
def test_load_section_documentation_prompts_for_every_section(file: str):
    prompt = load_prompt(file)

    assert isinstance(prompt, str), f"{file} prompt should be a string"
    assert isinstance(file, str), f"{file} response template should be a string"

    assert prompt.strip(), f"{file} prompt file is empty"

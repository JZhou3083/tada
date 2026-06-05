import pytest

from tada.domain.sections import WorkbookSection
from tada.prompts.loader import load_section_documentation_prompts


@pytest.fixture(autouse=True)
def clear_section_prompt_cache():
    load_section_documentation_prompts.cache_clear()
    yield
    load_section_documentation_prompts.cache_clear()


@pytest.mark.parametrize("section", list(WorkbookSection))
def test_load_section_documentation_prompts_for_every_section(section: WorkbookSection):
    prompt, response_template = load_section_documentation_prompts(section)

    assert isinstance(prompt, str), f"{section} prompt should be a string"
    assert isinstance(response_template, str), (
        f"{section} response template should be a string"
    )

    assert prompt.strip(), f"{section} prompt file is empty"
    assert response_template.strip(), f"{section} response template file is empty"

from __future__ import annotations

from functools import lru_cache
from importlib import resources

from tada.domain.sections import WorkbookSection

SECTIONS_PKG = "tada.prompts.sections"


@lru_cache(maxsize=None)
def load_section_documentation_prompts(section: WorkbookSection) -> tuple[str, str]:
    root = resources.files(SECTIONS_PKG)
    prompt = (root / f"{section.value}.prompt.md").read_text(encoding="utf-8")
    response_template = (root / f"{section.value}.response_template.md").read_text(
        encoding="utf-8"
    )
    return prompt, response_template

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import questionary
from prompt_toolkit.completion import PathCompleter
from questionary import ValidationError as QValidationError
from questionary import Validator


def make_questionary_path_validator(
    exists: bool,
    suffixes: str | tuple[str, ...],
) -> type[Validator]:
    class _Validator(Validator):
        def validate(self, document):
            if not document.text.lower().endswith(suffixes):
                display = ", ".join(repr(s) for s in suffixes)
                raise QValidationError(
                    message=f"Please select a file ending in {display}",
                    cursor_position=len(document.text),
                )

            if exists and not Path(document.text).is_file():
                raise QValidationError(
                    message="File does not exist", cursor_position=len(document.text)
                )

            if not exists and Path(document.text).is_file():
                raise QValidationError(
                    message="File already exists", cursor_position=len(document.text)
                )

    return _Validator


def make_questionary_path_completer(
    exists: bool, suffixes: str | tuple[str, ...]
) -> PathCompleter:
    if exists:
        return PathCompleter(
            file_filter=lambda f: f.endswith(suffixes) or Path(f).is_dir()
        )

    return PathCompleter(only_directories=True)


def ask_file_type(prompt: str, *, exists: bool, suffixes: str | Sequence[str]) -> Path:
    """Interactive prompt to select a file with only specific suffixes permitted"""
    suffixes = tuple(suffixes)
    report_path = questionary.path(
        prompt,
        completer=make_questionary_path_completer(exists, suffixes),
        validate=make_questionary_path_validator(exists, suffixes),
    ).unsafe_ask()
    return Path(report_path)

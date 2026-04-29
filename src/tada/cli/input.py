from __future__ import annotations

from pathlib import Path
from typing import Sequence

import questionary
from prompt_toolkit.completion import PathCompleter
from questionary import ValidationError as QValidationError
from questionary import Validator


def _normalise_suffixes(suffixes: str | Sequence[str]) -> tuple[str, ...]:
    """Return file suffixes as a lowercase tuple.

    Args:
        suffixes: A single file extension or a sequence of file extensions,
            such as ``".csv"`` or ``(".csv", ".xlsx")``.

    Returns:
        A tuple of lowercase suffix strings.
    """
    if isinstance(suffixes, str):
        return (suffixes.lower(),)
    return tuple(s.lower() for s in suffixes)


def build_file_path_validator(
    must_exist: bool,
    suffixes: str | tuple[str, ...],
) -> type[Validator]:
    """Create a Questionary validator for file path input.

    The returned validator ensures that:

    - the entered path ends with one of the allowed suffixes
    - the file exists when ``must_exist`` is ``True``
    - the file does not already exist when ``must_exist`` is ``False``

    Args:
        must_exist: If ``True``, the entered path must point to an existing file.
            If ``False``, the entered path must not already exist.
        suffixes: One or more permitted file extensions, for example
            ``".csv"`` or ``(".csv", ".xlsx")``.

    Raises:
        QValidationError: If the path does not end with an allowed suffix.
        QValidationError: If ``must_exist`` is ``True`` and the file does not exist.
        QValidationError: If ``must_exist`` is ``False`` and the file already exists.

    Returns:
        A ``questionary.Validator`` subclass suitable for use with
        ``questionary.path(..., validate=...)``.
    """

    class _Validator(Validator):
        def validate(self, document):
            if not document.text.lower().endswith(suffixes):
                display = ", ".join(repr(s) for s in suffixes)
                raise QValidationError(
                    message=f"Please select a file ending in {display}",
                    cursor_position=len(document.text),
                )

            if must_exist and not Path(document.text).is_file():
                raise QValidationError(
                    message="File does not exist",
                    cursor_position=len(document.text),
                )

            if not must_exist and Path(document.text).is_file():
                raise QValidationError(
                    message="File already exists",
                    cursor_position=len(document.text),
                )

    return _Validator


def build_file_path_completer(
    must_exist: bool,
    suffixes: str | tuple[str, ...],
) -> PathCompleter:
    """Create a path completer for file path prompts.

    When prompting for an existing file, completion includes directories and
    files matching the allowed suffixes.

    When prompting for a new file, completion is limited to directories so the
    user can navigate to the target location without suggesting existing files.

    Args:
        must_exist: If ``True``, autocomplete should suggest existing matching
            files. If ``False``, autocomplete should only help the user navigate
            directories for a new file path.
        suffixes: One or more permitted file extensions.

    Returns:
        A configured ``prompt_toolkit.completion.PathCompleter`` instance.
    """
    if must_exist:
        return PathCompleter(
            file_filter=lambda f: f.lower().endswith(suffixes) or Path(f).is_dir()
        )

    return PathCompleter(only_directories=True)


def ask_for_file_path(
    prompt: str,
    *,
    must_exist: bool,
    suffixes: str | Sequence[str],
) -> Path:
    """Prompt the user to enter a file path interactively.

    The prompt provides path autocompletion and validates that the entered path
    has an allowed suffix. It can be configured to require either an existing
    file or a new, non-existent file.

    Args:
        prompt: The message displayed to the user.
        must_exist: If ``True``, require the selected path to be an existing
            file. If ``False``, require the selected path not to exist yet.
        suffixes: A single allowed file extension or a sequence of allowed
            extensions.

    Returns:
        The selected file path as a ``pathlib.Path`` instance.
    """
    allowed_suffixes = _normalise_suffixes(suffixes)
    file_path = questionary.path(
        prompt,
        completer=build_file_path_completer(must_exist, allowed_suffixes),
        validate=build_file_path_validator(must_exist, allowed_suffixes),
    ).unsafe_ask()
    return Path(file_path)

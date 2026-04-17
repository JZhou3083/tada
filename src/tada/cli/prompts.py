from pathlib import Path

import questionary
from prompt_toolkit.completion import PathCompleter
from questionary import ValidationError as QValidationError
from questionary import Validator


class WorkbookValidator(Validator):
    def validate(self, document):
        if not document.text.lower().endswith(".twb"):
            raise QValidationError(
                message="Please select a file ending in .twb",
                cursor_position=len(document.text),
            )
        if not Path(document.text).is_file():
            raise QValidationError(
                message="File does not exist", cursor_position=len(document.text)
            )


workbook_completer = PathCompleter(
    file_filter=lambda f: f.lower().endswith(".twb") or Path(f).is_dir()
)


def ask_workbook_file(prompt: str) -> Path:
    """Interactive prompt to select a Tableau workbook file (.twb)."""
    report_path = questionary.path(
        prompt,
        completer=workbook_completer,
        validate=WorkbookValidator,
    ).ask()
    return Path(report_path)

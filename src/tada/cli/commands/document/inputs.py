from pathlib import Path

import questionary
from opentelemetry import trace
from questionary import Choice

from tada.cli.input import ask_for_file_path
from tada.cli.options import (
    AllSectionsOpt,
    OutputOpt,
    SectionOpt,
    WorkbookOpt,
)
from tada.cli.prompting import run_interactive_prompt
from tada.domain.sections import WorkbookSection

tracer = trace.get_tracer(__name__)


def resolve_workbook_arg(workbook_path: WorkbookOpt | None) -> Path:
    """Resolve the workbook path from CLI input or an interactive prompt.

    If a workbook path was provided on the command line, it is returned as-is.
    Otherwise, the user is prompted to enter the path to an existing Tableau
    workbook file.

    Args:
        workbook_path: The workbook path provided via the CLI, if any.

    Returns:
        The resolved path to an existing Tableau workbook file.

    Raises:
        typer.Exit: If the user cancels the interactive prompt.
    """
    if workbook_path:
        return workbook_path

    return run_interactive_prompt(
        "cli.prompt.workbook_path",
        lambda: ask_for_file_path(
            "Enter the path to your Tableau workbook (.twb or .twbx)",
            must_exist=True,
            suffixes=(".twb", ".twbx"),
        ),
    )


def resolve_output_arg(output_path: OutputOpt | None, workbook_path: Path) -> Path:
    """Resolve the output path from CLI input or an interactive prompt.

    If an output path was provided on the command line, it is returned as-is.
    Otherwise, the user is prompted to enter a new path for the generated
    Markdown file.

    Args:
        output_path: The output path provided via the CLI, if any.

    Returns:
        The resolved path for the generated Markdown output file.

    Raises:
        typer.Exit: If the user cancels the interactive prompt.
    """
    if output_path:
        return output_path

    default_output_path = str(Path("output") / workbook_path.with_suffix(".md").name)

    return run_interactive_prompt(
        "cli.prompt.output_path",
        lambda: ask_for_file_path(
            "Enter the path to save generated documentation to after completion (.md)",
            default=default_output_path,
            must_exist=False,
            suffixes=(".md",),
        ),
    )


# TODO: sections has been included to help with smaller tests, it should be removed from final product
def resolve_sections_arg(
    sections: SectionOpt | None,
    all_sections: AllSectionsOpt = False,
) -> list[WorkbookSection]:
    """Resolve which workbook sections should be documented.

    Section selection is resolved in the following order:

    1. If ``all_sections`` is enabled, all workbook sections are selected.
    2. If one or more sections were provided on the command line, those are used.
    3. Otherwise, the user is prompted to choose sections interactively.

    Args:
        sections: The sections provided via the CLI, if any.
        all_sections: Whether all sections should be included.

    Returns:
        The list of workbook sections to include in the documentation.

    Raises:
        typer.Exit: If the user cancels the interactive prompt.
    """
    if all_sections:
        return list(WorkbookSection)

    if sections:
        return sections

    choices = [Choice(title=s.value, value=s) for s in list(WorkbookSection)]

    return run_interactive_prompt(
        "cli.prompt.sections",
        lambda: questionary.checkbox(
            "Select sections to document",
            choices,
            validate=lambda selected: (
                len(selected) > 0
            ),  # Users must select at least one section
        ).unsafe_ask(),
    )


def prompt_for_summary_flag() -> bool:
    """Interactively prompt the user for whether or not to include a summary.

    Returns:
        The boolean user input.

    Raises:
        typer.Exit: If the user cancels the interactive prompt.
    """
    return run_interactive_prompt(
        "cli.prompt.summary",
        lambda: questionary.confirm(
            "Include a top-level summary of selected sections?"
        ).unsafe_ask(),
    )

import logging
from pathlib import Path

import questionary
import typer
from questionary import Choice
from rich.live import Live

from tada.cli.commands._base import AppCommand
from tada.cli.config import cli_config
from tada.cli.display import (
    GraphStatusDisplay,
    console,
    print_debug_notice,
    print_tada_banner,
)
from tada.cli.input import ask_for_file_path
from tada.cli.options import (
    AllSectionsOpt,
    DebugOpt,
    OutputOpt,
    SectionOpt,
    WorkbookOpt,
)
from tada.domain.workbook import Workbook, WorkbookSection
from tada.graph.events import GraphStatusEvent, GraphStatusStore
from tada.graph.state import InputState
from tada.graph.workflows.full_workbook import build_documentation_workflow

logger = logging.getLogger(__name__)


def _resolve_workbook_arg(workbook_path: WorkbookOpt | None) -> Path:
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

    try:
        return ask_for_file_path(
            "Enter the path to your Tableau workbook (.twb or .twbx)",
            must_exist=True,
            suffixes=(".twb", ".twbx"),
        )
    except KeyboardInterrupt:
        console.print("[yellow]Cancelled.")
        raise typer.Exit(code=0)


def _resolve_output_arg(output_path: OutputOpt | None, workbook_path: Path) -> Path:
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

    try:
        return ask_for_file_path(
            "Enter the path to save generated documentation to after completion (.md)",
            default=workbook_path.with_suffix(
                ".md"
            ).name,  # or str? which is appropriate
            must_exist=False,
            suffixes=(".md"),
        )
    except KeyboardInterrupt:
        console.print("[yellow]Cancelled.")
        raise typer.Exit(code=0)


# TODO: sections has been included to help with smaller tests, it should be removed from final product
def _resolve_sections_arg(
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
    try:
        return questionary.checkbox(
            "Select sections to document",
            choices,
            validate=lambda a: len(a) > 0,  # Users must select at least one section
        ).unsafe_ask()
    except KeyboardInterrupt:
        console.print("[yellow]Cancelled.")
        raise typer.Exit(code=0)


def run_document(
    workbook_path: WorkbookOpt = None,
    output_path: OutputOpt = None,
    sections: SectionOpt = None,
    all_sections: AllSectionsOpt = False,
) -> None:
    """Generate Markdown documentation for a Tableau workbook.

    This function resolves all required inputs, parses the workbook, invokes the
    documentation workflow, and writes the generated documentation to disk.

    If any required inputs are not supplied via CLI options, the user is prompted
    for them interactively.

    Args:
        workbook_path: Path to the Tableau workbook to document.
        output_path: Path where the generated Markdown should be written.
        sections: Specific workbook sections to document.
        all_sections: Whether to document all available workbook sections.
    """
    workbook_path = _resolve_workbook_arg(workbook_path)
    output_path = _resolve_output_arg(output_path, workbook_path)
    sections = _resolve_sections_arg(sections, all_sections)
    include_summary = questionary.confirm(
        "Include a top-level summary of selected sections?"
    ).ask()
    # max_retries = questionary.select(
    #     "Choose the permitted number of generation retries"
    # )
    # max_retries = questionary.select(
    #     "Choose whether to enable evaluation if 0 retries?"
    # )

    # Pre-process the workbook using our pre-existing XML -> JSON parsing approach
    logger.debug("Parsing workbook: %s", workbook_path)
    workbook = Workbook.from_file(workbook_path)
    logger.debug("Parsed workbook.")

    if cli_config.debug:
        workbook.write_debug(cli_config.debug_dir)
        logger.debug("Wrote parsed workbook contents to %s", cli_config.debug_dir)

    workflow = build_documentation_workflow()
    workflow_input = InputState(
        workbook=workbook,
        generation_plan=sections,
        run_summary_step=include_summary,
    )

    logger.debug(
        "Invoking documentation graph...",
    )

    statuses = GraphStatusStore()
    display = GraphStatusDisplay(total_sections=len(sections))

    with Live(
        display.build(statuses),
        refresh_per_second=10,
        console=console,
    ) as live:

        def refresh():
            live.update(display.build(statuses))

        documentation = None

        for chunk in workflow.stream(
            input=workflow_input,
            stream_mode=["custom", "values"],
            subgraphs=True,
            version="v2",
        ):
            if chunk["type"] == "custom":
                status_update: GraphStatusEvent = chunk["data"]
                statuses.apply(status_update)

                refresh()

            elif chunk["type"] == "values":
                documentation: str | None = chunk["data"].get("final_doc")

    logger.debug("Graph complete.")

    if not documentation:
        raise ValueError("Expected key `final_doc` not found in graph output")

    output_path.write_text(documentation)

    console.print(f"[green]✔[/green] Documentation exported → {output_path.name}")


def _cmd_document(
    workbook_path: WorkbookOpt = None,
    output_path: OutputOpt = None,
    sections: SectionOpt = None,
    all_sections: AllSectionsOpt = False,
    debug: DebugOpt = False,
) -> None:
    """CLI entry point for the ``document`` command.

    This wrapper applies CLI configuration, enables debug behaviour when
    requested, prints command-line UI elements, and then runs the documentation
    workflow.

    Args:
        workbook_path: Path to the Tableau workbook to document.
        output_path: Path where the generated Markdown should be written.
        sections: Specific workbook sections to document.
        all_sections: Whether to document all available workbook sections.
        debug: Whether to enable debug logging and debug artifact output.
    """
    cli_config.apply_debug(debug)
    cli_config.configure_logging(console)
    print_tada_banner(
        console,
        subtitle="Documentation generator",
    )
    if cli_config.debug:
        print_debug_notice(console, debug_dir=cli_config.debug_dir)
    run_document(workbook_path, output_path, sections, all_sections)


def register(app: typer.Typer) -> None:
    """Register the ``document`` command with the Typer application.

    Args:
        app: The Typer application to register the command with.
    """
    app.command(
        name="document",
        help="Document a Tableau workbook using a standardized workflow.",
    )(_cmd_document)


COMMAND = AppCommand(
    name="document",
    interactive_menu_desc="Generate workbook documentation",
    register=register,
    run=run_document,
)

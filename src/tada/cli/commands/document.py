import logging
from pathlib import Path

import questionary
import typer
from questionary import Choice
from rich.live import Live

from tada.application.document_workbook import (
    DocumentWorkbookRequest,
    document_workbook,
)
from tada.cli.commands.base import AppCommand
from tada.cli.display.banners import print_command_header
from tada.cli.display.console import console
from tada.cli.display.documentation_progress import DocumentationProgressDisplay
from tada.cli.display.documentation_progress_sink import RichDocumentationProgressSink
from tada.cli.input import ask_for_file_path
from tada.cli.options import (
    AllSectionsOpt,
    OutputOpt,
    SectionOpt,
    WorkbookOpt,
)
from tada.cli.state import TadaCliState, get_cli_state
from tada.domain.sections import WorkbookSection
from tada.graph.events import GraphStatusStore

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

    default_output_path = str(Path("output") / workbook_path.with_suffix(".md").name)
    try:
        return ask_for_file_path(
            "Enter the path to save generated documentation to after completion (.md)",
            default=default_output_path,
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
    cli_state: TadaCliState,
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
        cli_state: CLI state for the current TaDA execution.
        workbook_path: Path to the Tableau workbook to document.
        output_path: Path where the generated Markdown should be written.
        sections: Specific workbook sections to document.
        all_sections: Whether to document all available workbook sections.
    """
    workbook_path = _resolve_workbook_arg(workbook_path)
    output_path = _resolve_output_arg(output_path, workbook_path)
    sections = _resolve_sections_arg(sections, all_sections)
    run_summary_step = questionary.confirm(
        "Include a top-level summary of selected sections?"
    ).ask()
    # max_retries = questionary.select(
    #     "Choose the permitted number of generation retries"
    # )
    # max_retries = questionary.select(
    #     "Choose whether to enable evaluation if 0 retries?"
    # )

    request = DocumentWorkbookRequest(
        workbook_path=workbook_path,
        output_path=output_path,
        sections=sections,
        run_summary_step=run_summary_step,
    )
    status_store = GraphStatusStore.from_sections([s.value for s in sections])
    display = DocumentationProgressDisplay(total_sections=len(sections))

    with Live(
        display.render(status_store), console=console, refresh_per_second=8
    ) as live:
        sink = RichDocumentationProgressSink(
            display=display, store=status_store, live=live
        )
        # TODO: can now pass in context vars e.g. `checkpointer_dir=run_context.checkpointer_dir`
        result = document_workbook(
            request,
            status_sink=sink,
        )

    console.print(f"[green]Documentation written to {result.output_path}[/green]")


def handle_document(
    ctx: typer.Context,
    workbook_path: WorkbookOpt = None,
    output_path: OutputOpt = None,
    sections: SectionOpt = None,
    all_sections: AllSectionsOpt = False,
) -> None:
    """Handle execution of the document command from any CLI route.

    This function is shared by direct command invocation and the interactive menu. It
    retrieves the current TaDA CLI state from the Typer context and delegates to the
    documentation workflow.

    Args:
        ctx: Typer context containing the current TaDA CLI state.
        workbook_path: Path to the Tableau workbook to document.
        output_path: Path where the generated Markdown should be written.
        sections: Specific workbook sections to document.
        all_sections: Whether to document all available workbook sections.
    """
    cli_state = get_cli_state(ctx)
    run_document(
        cli_state=cli_state,
        workbook_path=workbook_path,
        output_path=output_path,
        sections=sections,
        all_sections=all_sections,
    )


def _cmd_document(
    ctx: typer.Context,
    workbook_path: WorkbookOpt = None,
    output_path: OutputOpt = None,
    sections: SectionOpt = None,
    all_sections: AllSectionsOpt = False,
) -> None:
    """CLI entry point for the ``document`` command.

    This wrapper performs command-line UI setup, then delegates to the shared
    document handler used by both direct invocation and the interactive menu.

    Args:
        ctx: Typer context containing the current TaDA CLI state.
        workbook_path: Path to the Tableau workbook to document.
        output_path: Path where the generated Markdown should be written.
        sections: Specific workbook sections to document.
        all_sections: Whether to document all available workbook sections.
    """
    print_command_header(
        ctx,
        console,
        subtitle="Documentation generator",
    )

    handle_document(
        ctx=ctx,
        workbook_path=workbook_path,
        output_path=output_path,
        sections=sections,
        all_sections=all_sections,
    )


def register(app: typer.Typer) -> None:
    """Register the ``document`` command with the Typer app.

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
    run=handle_document,
)

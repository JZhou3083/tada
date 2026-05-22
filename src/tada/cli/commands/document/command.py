import logging

import typer
from opentelemetry import trace

from tada.cli.commands.base import AppCommand
from tada.cli.commands.document.run import run_document
from tada.cli.display.banners import print_command_header
from tada.cli.display.console import console
from tada.cli.options import (
    AllSectionsOpt,
    OutputOpt,
    SectionOpt,
    WorkbookOpt,
)
from tada.cli.state import get_cli_state

tracer = trace.get_tracer(__name__)

logger = logging.getLogger(__name__)


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

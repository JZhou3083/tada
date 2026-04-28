import logging

import questionary
import typer
from questionary import Choice

from tada.cli.commands._base import AppCommand
from tada.cli.config import cli_config
from tada.cli.display import console, print_debug_notice, print_tada_banner
from tada.cli.input import ask_workbook_file
from tada.cli.options import DebugOpt, WorkbookOpt
from tada.domain.workbook import Workbook, WorkbookSection
from tada.graph.state import InputState
from tada.graph.workflow import build_documentation_workflow

logger = logging.getLogger(__name__)


def run_document(workbook_path: WorkbookOpt = None) -> None:
    """
    Generate documentation for a Tableau workbook.
    If no workbook is provided via the CLI, the user is prompted to select one.
    """
    # Prompt users to select a workbook if one wasn't provided as a CLI argument
    if not workbook_path:
        try:
            workbook_path = ask_workbook_file(
                "Enter the path to your Tableau workbook (.twb or .twbx)"
            )
        except KeyboardInterrupt:
            console.print("[yellow]Cancelled.")
            raise typer.Exit(code=0)

    # Pre-process the workbook using our pre-existing XML -> JSON parsing approach
    logger.debug("Parsing workbook: %s", workbook_path)
    workbook = Workbook.from_file(workbook_path)
    logger.debug("Parsed workbook.")
    console.print("[green]✔[/green] Processed workbook.")

    if cli_config.debug:
        workbook.write_debug(cli_config.debug_dir)
        logger.debug("Wrote parsed workbook contents to %s", cli_config.debug_dir)

    choices = [Choice(title=s.value, value=s) for s in list(WorkbookSection)]
    try:
        selected_sections = questionary.checkbox(
            "Select sections to document",
            choices,
        ).unsafe_ask()
    except KeyboardInterrupt:
        console.print("[yellow]Cancelled.")
        raise typer.Exit(code=0)

    with console.status("Generating documentation...", spinner="dots"):
        workflow = build_documentation_workflow()
        workflow_input = InputState(
            workbook=workbook,
            generation_plan=selected_sections,
        )

        logger.debug(
            "Invoking documentation graph...",
        )
        result = workflow.invoke(workflow_input)
        logger.debug("Graph complete.")

    output = {k: v for k, v in result.items() if k != "workbook"}

    console.print("[green]✔[/green] Generated response:")
    console.print_json(data=output)

    # TODO: determine actual export logic
    console.print("[green]✔[/green] Documentation exported → ???")


def _cmd_document(workbook_path: WorkbookOpt = None, debug: DebugOpt = False) -> None:
    cli_config.apply_debug(debug)
    cli_config.configure_logging(console)
    print_tada_banner(
        console,
        subtitle="Documentation generator",
    )
    if cli_config.debug:
        print_debug_notice(console, debug_dir=cli_config.debug_dir)
    run_document(workbook_path)


def register(app: typer.Typer) -> None:
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

import json

import typer
from rich.console import Console

from tada.cli.commands._base import AppCommand
from tada.cli.display import print_tada_banner
from tada.cli.input import ask_workbook_file
from tada.cli.options import WorkbookOpt
from tada.domain.workbook import Workbook
from tada.domain.workbook_sections import WorkbookSection
from tada.graph.state import State
from tada.graph.workflow import build_documentation_workflow

console = Console()


def run_document(workbook_path: WorkbookOpt = None) -> None:
    """
    Generate documentation for a Tableau workbook.
    If no workbook is provided via the CLI, the user is prompted to select one.
    """
    # Prompt users to select a workbook if one wasn't provided as a CLI argument
    if not workbook_path:
        workbook_path = ask_workbook_file("Select a Tableau workbook (.twb or .twbx)")

    # Pre-process the workbook using our pre-existing XML -> JSON parsing approach
    workbook = Workbook.from_file(workbook_path)
    console.print("[green]✔[/green] Processed workbook.")

    with console.status("Generating documentation...", spinner="dots"):
        workflow = build_documentation_workflow()
        workflow_input = State(
            workbook=workbook,
            generation_plan=[WorkbookSection.DATASOURCES, WorkbookSection.DASHBOARDS],
            generated_docs={},
        )

        result = workflow.invoke(workflow_input)

    del result["workbook"]

    console.print("[green]✔[/green] Generated response:")
    console.print_json(json=json.dumps(result))

    # TODO: determine actual export logic
    console.print("[green]✔[/green] Documentation exported → ???")


def register(app: typer.Typer) -> None:
    @app.command(
        name="document",
        help="Document a Tableau workbook using a standardized workflow.",
    )
    def cmd_document(workbook_path: WorkbookOpt = None) -> None:
        print_tada_banner(console, subtitle="Documentation generator")
        run_document(workbook_path)


COMMAND = AppCommand(
    name="document",
    interactive_menu_desc="Generate workbook documentation",
    register=register,
    run=run_document,
)

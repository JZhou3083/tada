import typer
from rich.console import Console

from tada.cli.input import ask_workbook_file
from tada.cli.options import WorkbookOpt
from tada.domain.workbook import Workbook

console = Console()


def register(app: typer.Typer) -> None:
    @app.command(
        name="document",
        help="Document a Tableau workbook using a standardized workflow.",
    )
    def cmd_document_workbook(
        workbook_path: WorkbookOpt = None,
    ) -> None:
        """
        Generate documentation for a Tableau workbook.

        If no workbook is provided via the CLI, , the user is prompted to select one
        interactively. The workbook is then parsed and passed into the documentation
        workflow.
        """

        # Prompt users to select a workbook if one wasn't provided as a CLI argument
        if not workbook_path:
            workbook_path = ask_workbook_file("Select a Tableau workbook (.twb)")

        # Pre-process the workbook using our pre-existing XML -> JSON parsing approach
        workbook = Workbook.from_file(workbook_path)
        console.print("[green]✔[/green] Processed notebook.")

        print(workbook)

        # TODO: convert this from a mockup to actually generating documentation
        # with console.status("Generating documentation...", spinner="dots"):
        #     time.sleep(2)

        #     graph_input = State(workbook=workbook)
        #     result = graph.invoke(graph_input)

        # console.print("[green]✔[/green] Generated response:")
        # console.print_json(json=json.dumps(result))

        # TODO: determine actual export logic
        console.print("[green]✔[/green] Documentation exported → ???")

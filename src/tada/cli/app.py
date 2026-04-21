import typer
from rich.console import Console

from tada.cli.commands.document import register as register_document

app = typer.Typer(
    name="Tableau Documentation Agent",
    no_args_is_help=True,
    help="CLI interface for the Tableau Documentation Agent.",
    add_completion=True,
)
console = Console()

register_document(app)


@app.command(
    name="compare",
    help="Review differences between two or more Tableau workbooks.",
)
def compare_workbooks():
    # TODO: create comparison logic or delete command
    console.print(
        "[yellow]Command not yet available.[/yellow] "
        "Workbook comparison is still under development."
    )
    raise typer.Exit(0)


@app.command(
    name="chat",
    help="Ask questions about a Tableau workbook in a free-form conversation.",
)
def chat_with_workbooks():
    # TODO: create chat logic or delete command
    console.print(
        "[yellow]Command not yet available.[/yellow] "
        "Chat features are still under development."
    )
    raise typer.Exit(0)


def main():
    app()

import typer
from rich.console import Console

from tada.cli.commands.chat import register as register_chat
from tada.cli.commands.compare import register as register_compare
from tada.cli.commands.document import register as register_document

app = typer.Typer(
    name="Tableau Documentation Agent",
    no_args_is_help=True,
    help="CLI interface for the Tableau Documentation Agent.",
    add_completion=True,
)
console = Console()

register_document(app)
register_chat(app)
register_compare(app)


def main():
    app()

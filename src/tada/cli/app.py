import questionary
import typer
from questionary import Choice
from rich.console import Console

from tada.cli.commands.chat import COMMAND as CHAT_COMMAND
from tada.cli.commands.compare import COMMAND as COMPARE_COMMAND
from tada.cli.commands.document import COMMAND as DOCUMENT_COMMAND
from tada.cli.display import print_tada_banner

app = typer.Typer(
    name="Tableau Documentation Agent (TaDA)",
    no_args_is_help=False,
    rich_markup_mode="rich",
    epilog=(
        "[bold cyan]Tip:[/bold cyan] Run [bold]tada[/bold] with no arguments to "
        "launch the interactive menu."
    ),
)
console = Console()


ALL_COMMANDS = [DOCUMENT_COMMAND, CHAT_COMMAND, COMPARE_COMMAND]
APP_COMMANDS = {cmd.name: cmd.run for cmd in ALL_COMMANDS}


@app.callback(invoke_without_command=True)
def menu(ctx: typer.Context):
    """
    LLM-powered CLI tool for documenting and discussing Tableau workbooks.
    """

    # If a subcommand was provided then proceed as normal
    if ctx.invoked_subcommand is not None:
        return

    # No subcommand -> route to the interactive launcher
    interactive_launcher()


def interactive_launcher():
    print_tada_banner(
        console,
        subtitle="Interactive menu",
        hint="Tip: Use ↑/↓ to move, Enter to select, Ctrl+C to quit.",
    )
    choices = [
        Choice(
            title=[
                ("bold", c.name),
                ("", ": "),
                ("fg:ansibrightblack", c.interactive_menu_desc),
            ],
            value=c.name,
        )
        for c in ALL_COMMANDS
    ]
    selected = questionary.select(
        "What do you want to do?", choices, instruction=" "
    ).ask()

    try:
        APP_COMMANDS[selected]()
    except KeyError:
        console.print("[bold red]Error[/bold red] Unknown command selected.")
        raise typer.Exit(code=0)


for cmd in ALL_COMMANDS:
    cmd.register(app)


def main():
    app()

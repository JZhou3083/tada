import questionary
import typer
from questionary import Choice

from tada.cli.commands.chat import COMMAND as CHAT_COMMAND
from tada.cli.commands.compare import COMMAND as COMPARE_COMMAND
from tada.cli.commands.document import COMMAND as DOCUMENT_COMMAND
from tada.cli.config import cli_config
from tada.cli.display import console, print_debug_notice, print_tada_banner
from tada.cli.options import DebugOpt

app = typer.Typer(
    name="Tableau Documentation Agent (TaDA)",
    no_args_is_help=False,
    rich_markup_mode="rich",
    epilog=(
        "[bold cyan]Tip:[/bold cyan] Run [bold]tada[/bold] with no arguments to "
        "launch the interactive menu."
    ),
)


ALL_COMMANDS = [DOCUMENT_COMMAND, CHAT_COMMAND, COMPARE_COMMAND]
APP_COMMANDS = {cmd.name: cmd.run for cmd in ALL_COMMANDS}


@app.callback(invoke_without_command=True)
def menu(
    ctx: typer.Context,
    debug: DebugOpt = False,
):
    """
    LLM-powered CLI tool for documenting and discussing Tableau workbooks.
    """
    # Apply debug status globally so subcommands can access it
    cli_config.apply_debug(debug)

    # If a subcommand was provided then proceed as normal
    if ctx.invoked_subcommand is not None:
        return

    # No subcommand -> route to the interactive launcher
    print_tada_banner(
        console,
        subtitle="Interactive menu",
    )
    if cli_config.debug:
        print_debug_notice(console, debug_dir=cli_config.debug_dir)
    interactive_launcher()


def interactive_launcher():
    """
    Prompt user to select one of the TaDA commands from an interactive menu and run it.
    """
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
    # Add an exit option
    choices.append(
        Choice(
            title=[
                ("bold", "exit"),
                ("", ": "),
                ("fg:ansibrightblack", "Quit the application"),
            ],
            value="exit",
        )
    )

    try:
        selected = questionary.select(
            "What do you want to do?",
            choices,
        ).unsafe_ask()
    except KeyboardInterrupt:
        console.print("[yellow]Cancelled.")
        raise typer.Exit(code=0)

    if selected == "exit":
        console.print("[yellow]Cancelled.")
        raise typer.Exit(code=0)

    handler = APP_COMMANDS.get(selected)
    if handler is None:
        console.print("[bold red]Error[/bold red] Unknown command selected.")
        raise typer.Exit(code=1)

    handler()


def main():
    for cmd in ALL_COMMANDS:
        cmd.register(app)

    app()

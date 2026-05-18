import questionary
import typer
from questionary import Choice

from tada.cli.commands._base import AppCommand
from tada.cli.display.console import console


def prompt_for_command(ctx: typer.Context, commands: list[AppCommand]):
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
        for c in commands
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

    cmd = next((c for c in commands if c.name == selected), None)
    handler = cmd.run if cmd else None
    if handler is None:
        console.print("[bold red]Error[/bold red] Unknown command selected.")
        raise typer.Exit(code=1)

    handler(ctx=ctx)

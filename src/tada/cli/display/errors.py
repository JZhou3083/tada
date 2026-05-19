from rich.console import Console
from rich.panel import Panel


def print_typer_error(console: Console, message: str) -> None:
    console.print(
        Panel(
            message,
            title="Error",
            title_align="left",
            border_style="red",
        )
    )

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def print_tada_banner(
    console: Console,
    *,
    subtitle: str | None = None,
) -> None:
    title = Text()
    title.append("TaDA", style="bold cyan")
    title.append("  ", style="")
    title.append("Tableau Documentation Agent", style="bold")

    body = Text()
    body.append_text(title)

    if subtitle:
        sub = Text(subtitle, style="dim")
        body.append("\n")
        body.append_text(sub)

    console.print(
        Panel(
            Align.left(body),
            border_style="cyan",
            padding=(1, 2),
        )
    )

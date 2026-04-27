from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def print_tada_banner(
    console: Console,
    *,
    subtitle: str | None = None,
    hint: str | None = "↑/↓ Navigate • Enter Select • Ctrl+C Exit",
) -> None:
    title = Text()
    title.append("TaDA", style="bold cyan")
    title.append("  Tableau Documentation Agent", style="bold")

    body = Text()
    body.append_text(title)

    if subtitle:
        subtitle_text = Text(subtitle, style="dim")
        body.append("\n")
        body.append_text(subtitle_text)

    if hint:
        hint_text = Text(hint, style="italic grey70")
        body.append("\n")
        body.append_text(hint_text)

    console.print(
        Panel(
            Align.left(body),
            border_style="cyan",
            padding=(1, 2),
        ),
    )

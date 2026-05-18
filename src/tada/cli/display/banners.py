from pathlib import Path

import typer
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from tada.cli.state import get_cli_state


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


def print_debug_notice_banner(console: Console, debug_dir: Path) -> None:
    body = Text()
    body.append("Debug mode active\n", style="bold yellow")
    body.append("Artifacts will be written to ", style="dim")
    body.append(str(debug_dir), style="cyan")

    console.print(
        Panel(
            body,
            border_style="yellow",
            padding=(0, 2),
        )
    )


def print_command_header(
    ctx: typer.Context,
    console: Console,
    *,
    subtitle: str | None = None,
    hint: str | None = "↑/↓ Navigate • Enter Select • Ctrl+C Exit",
) -> None:
    """Print the standard CLI header for a command, including debug notice if enabled."""
    print_tada_banner(
        console,
        subtitle=subtitle,
        hint=hint,
    )

    state = get_cli_state(ctx)
    if state.cli_options.debug:
        print_debug_notice_banner(
            console,
            debug_dir=state.run_context.info.run_dir,
        )

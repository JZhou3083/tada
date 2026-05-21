from rich.console import Console, RenderableType
from rich.panel import Panel


def print_typer_error(
    console: Console, message: str | RenderableType, *, markup: bool = False
) -> None:
    if isinstance(message, str):
        renderable: RenderableType = message
        use_markup = markup
    else:
        # Already a rich object → don't apply markup handling
        renderable = message
        use_markup = False

    console.print(
        Panel(
            renderable,
            title="Error",
            title_align="left",
            border_style="red",
        ),
        markup=use_markup,
    )

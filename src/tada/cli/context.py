import typer

from tada.runtime.context import TadaRunContext


def get_run_context(ctx: typer.Context) -> TadaRunContext:
    """Return the TaDA runtime context stored on the Typer context."""
    if not isinstance(ctx.obj, TadaRunContext):
        raise RuntimeError("TaDA runtime context was not initialised.")
    return ctx.obj

from dataclasses import dataclass

import typer

from tada.runtime.context import TadaRunContext


@dataclass(frozen=True)
class TadaCliOptions:
    """Global CLI options for a single TaDA invocation.

    These options are parsed from the root TaDA command and apply across the
    whole invocation, regardless of which subcommand is eventually executed.

    This class intentionally does not include subcommand-specific parameters.
    For example, in:

        tada --debug document --input input.md

    ``debug`` belongs here because it is a root-level option, while ``input``
    belongs to the ``document`` command/request model.

    The object is frozen so command handlers can safely read invocation-level
    behaviour without mutating global CLI state.
    """

    debug: bool = False
    """Whether debug mode is enabled for this CLI invocation."""


@dataclass(frozen=True)
class TadaCliState:
    """Shared Typer context state for a single TaDA CLI invocation.

    This object is stored on ``typer.Context.obj`` by the root callback and is
    used by command handlers to access shared invocation state without relying
    on module-level globals.

    It contains only cross-cutting state needed at the CLI boundary:

    - ``run_context``: identifies the current run and provides per-run paths.
    - ``cli_options``: root-level CLI behaviour flags, such as debug mode.

    Command-specific arguments should not be added here. They should remain in
    the relevant Typer command parameters or be converted into command/request
    objects before entering application logic.
    """

    run_context: TadaRunContext
    """Per-run context containing invocation identity and filesystem layout."""

    cli_options: TadaCliOptions
    """Root-level CLI options for this invocation."""


def get_cli_state(ctx: typer.Context) -> TadaCliState:
    """Return the TaDA CLI state stored on the Typer context."""
    if not isinstance(ctx.obj, TadaCliState):
        raise RuntimeError("TaDA CLI state was not initialised.")
    return ctx.obj

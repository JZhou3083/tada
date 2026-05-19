from collections.abc import Callable
from typing import TypeVar

import typer
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry import trace

from tada.cli.display.console import console

tracer = trace.get_tracer(__name__)

T = TypeVar("T")


def run_interactive_prompt(
    span_name: str,
    prompt: Callable[[], T | None],
) -> T:
    """Run an interactive CLI prompt with tracing and cancellation handling.

    Args:
        span_name: Name of the tracing span to create for the prompt.
        prompt: Callable that executes the interactive prompt and returns its result.

    Returns:
        The prompt result.

    Raises:
        typer.Exit: If the user cancels the prompt.
    """
    try:
        with tracer.start_as_current_span(span_name) as prompt_span:
            prompt_span.set_attribute(
                SpanAttributes.OPENINFERENCE_SPAN_KIND,
                OpenInferenceSpanKindValues.CHAIN.value,
            )

            result = prompt()

    except KeyboardInterrupt:
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(code=0)

    if result is None:
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(code=0)

    return result

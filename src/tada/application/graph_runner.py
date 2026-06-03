from langchain_core.runnables import RunnableConfig
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry import trace

from tada.application.ports import StatusSink
from tada.graph.config import GraphContext
from tada.graph.events import GraphStatusEvent
from tada.graph.workbook_documenter import (
    WorkbookDocumenterGraph,
    WorkbookDocumenterInput,
    WorkbookDocumenterOutput,
)

tracer = trace.get_tracer(__name__)


def run_workbook_documenter_graph_with_status(
    *,
    graph: WorkbookDocumenterGraph,
    input: WorkbookDocumenterInput,
    context: GraphContext,
    status_sink: StatusSink,
    config: RunnableConfig | None = None,
) -> WorkbookDocumenterOutput:
    """Run the workbook documenter graph and forward status events.

    Streams the graph using both ``values`` and ``custom`` stream modes. Custom
    events matching ``GraphStatusEvent`` are passed to ``status_sink`` as they
    are emitted. The latest values chunk is treated as the final graph output
    and returned once execution completes.

    Args:
        graph: Compiled workbook documenter graph to execute.
        input: Initial input for the graph.
        context: Run-scoped graph context, including shared dependencies.
        status_sink: Sink used to handle streamed graph status events.
        config: Optional LangGraph/LangChain runtime config, such as
            ``thread_id``, callbacks, tags, metadata, or other configurable
            values.

    Returns:
        Final workbook documenter output emitted by the graph.

    Raises:
        RuntimeError: If the graph completes without emitting a final values
            chunk.
    """
    final_state = None

    with tracer.start_as_current_span("langgraph.run") as span:
        span.set_attribute(
            SpanAttributes.OPENINFERENCE_SPAN_KIND,
            OpenInferenceSpanKindValues.CHAIN.value,
        )

        for chunk in graph.stream(
            input,
            config=config,
            context=context,
            stream_mode=["values", "custom"],
            subgraphs=True,
            version="v2",
        ):
            if chunk["type"] == "custom":
                if isinstance(chunk["data"], GraphStatusEvent):
                    status_sink.handle(chunk["data"])

            elif chunk["type"] == "values":
                final_state = chunk["data"]

    if final_state is None:
        raise RuntimeError("Documentation workflow completed without final state")

    return final_state

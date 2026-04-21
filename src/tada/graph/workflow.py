from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from tada.graph.nodes import mock_llm
from tada.graph.state import State


def build_documentation_workflow() -> CompiledStateGraph:
    """Construct and compile the LangGraph workflow for workbook documentation.

    This function creates the workflow definition from scratch and returns a
    compiled graph ready to be invoked with a ``State`` payload.

    The workflow is currently a simple linear pipeline with a single
    ``mock_llm`` node:

    ``START -> mock_llm -> END``

    Returns:
        A compiled LangGraph workflow that accepts ``State`` as input.
    """
    builder = StateGraph(State)

    builder.add_node("mock_llm", mock_llm)

    builder.add_edge(START, "mock_llm")
    builder.add_edge("mock_llm", END)

    return builder.compile()

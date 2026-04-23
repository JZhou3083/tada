from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from tada.graph.ids import NodeId
from tada.graph.nodes import (
    generate_section_docs,
    plan_doc_generation,
)
from tada.graph.routers import route_plan_to_workers
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

    builder.add_node(NodeId.PLAN, plan_doc_generation)
    builder.add_node(NodeId.SUMMARIZE, generate_section_docs)

    builder.add_edge(START, NodeId.PLAN)
    builder.add_conditional_edges(NodeId.PLAN, route_plan_to_workers)
    builder.add_edge(NodeId.SUMMARIZE, END)

    return builder.compile()

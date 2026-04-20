from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    query: str
    response: NotRequired[str]


class StateUpdate(TypedDict, total=False):
    query: str
    response: str


def mock_llm(state: State) -> StateUpdate:
    return {"response": f"Dummy response to query '{state['query']}'"}


builder = StateGraph(State)

builder.add_node(mock_llm)

builder.add_edge(START, "mock_llm")
builder.add_edge("mock_llm", END)

graph = builder.compile()

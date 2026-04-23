from __future__ import annotations

from tada.graph.state import ComponentSummarizerState, State, StateUpdate


def plan_doc_generation(state: State) -> StateUpdate:
    return {"generation_plan": ["datasources", "worksheets", "tables"]}


def generate_section_docs(state: ComponentSummarizerState) -> StateUpdate:
    match state["component"]:
        case "datasources":
            return {"generated_docs": {"datasources": "dummy text"}}
        case "calculations":
            return {"generated_docs": {"calculations": "dummy text"}}
        case "dashboards":
            return {"generated_docs": {"dashboards": "dummy text"}}
        case "worksheets":
            return {"generated_docs": {"worksheets": "dummy text"}}
        case "actions":
            return {"generated_docs": {"actions": "dummy text"}}
        case "parameters":
            return {"generated_docs": {"parameters": "dummy text"}}
        case "tables":
            return {"generated_docs": {"tables": "dummy text"}}
        case _:
            raise ValueError

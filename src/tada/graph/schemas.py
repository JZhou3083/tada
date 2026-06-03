from dataclasses import dataclass

from tada.llm.gateway import ResponseMetadata


# TODO: same here to add graph_name?
@dataclass(frozen=True)
class LLMCallEvent:
    node_name: str
    metadata: ResponseMetadata
    section_subgraph: str | None = None
    section_attempt: int = 0

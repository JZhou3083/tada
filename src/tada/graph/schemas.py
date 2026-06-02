from dataclasses import dataclass

from tada.llm.gateway import ResponseMetadata


@dataclass(frozen=True)
class LLMCallEvent:
    node_name: str
    metadata: ResponseMetadata
    section_subgraph: str | None = None
    section_attempt: int = 0

from dataclasses import dataclass

from tada.llm.gateway import ResponseMetadata


@dataclass(frozen=True)
class LLMCallRecord:
    graph_name: str
    node_name: str
    metadata: ResponseMetadata
    section_name: str | None = None
    attempt: int | None = None

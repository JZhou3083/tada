from enum import StrEnum


class SectionNodeId(StrEnum):
    PREPARE_SECTION = "prepare_section"
    GENERATE_SECTION_DOCS = "generate_section_docs"
    EVALUATE_SECTION_DOCS = "evaluate_section_docs"
    EMIT_SECTION_DOCS = "emit_section_docs"
    EMIT_SECTION_DOCS_AFTER_RETRY_LIMIT = "emit_section_docs_after_retry_limit"
    EMIT_SECTION_DOCS_SKIPPED = "emit_section_docs_skipped"

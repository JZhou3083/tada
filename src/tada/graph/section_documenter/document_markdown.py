from collections.abc import Sequence
from textwrap import dedent

from tada.llm.schemas import BlockingIssue, EvalResult

_UNRESOLVED_ISSUES_WARNING_HEADING_MD = dedent("""
    > [!WARNING]
    > This section was emitted with unresolved blocking issues from the latest evaluation.
    >
    > Blocking issues:
""")


def _unresolved_blocking_issues_warning_md(
    issues: Sequence[BlockingIssue],
) -> str:
    """Create a Markdown warning for unresolved blocking issues."""
    issues_text = "\n".join(f"> - `{issue.type}`: {issue.item}" for issue in issues)

    if not issues_text:
        return _UNRESOLVED_ISSUES_WARNING_HEADING_MD

    return f"{_UNRESOLVED_ISSUES_WARNING_HEADING_MD}\n{issues_text}"


def prepend_unresolved_blocking_issues_warning_md(
    *,
    doc: str,
    eval_result: EvalResult | None,
) -> str:
    """Prepend unresolved blocking issues to a document, when present."""
    if eval_result is None or not eval_result.blocking_issues:
        return doc

    warning = _unresolved_blocking_issues_warning_md(eval_result.blocking_issues)

    return f"{warning}\n\n{doc}"

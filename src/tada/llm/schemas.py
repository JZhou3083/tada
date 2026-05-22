from typing import Literal

from pydantic import BaseModel, Field

BlockingIssueType = Literal[
    "hallucination",
    "critical_omission",
    "accuracy_error",
]

NonBlockingIssueType = Literal[
    "benign_omission",
    "style_redundancy",
    "readability",
]


class BlockingIssue(BaseModel):
    type: BlockingIssueType = Field(
        description=(
            "Blocking issue type: "
            "'hallucination' = claim not supported by source JSON; "
            "'critical_omission' = required template content missing from the documentation; "
            "'accuracy_error' = content is present but factually incorrect."
        )
    )
    item: str = Field(
        description=(
            "Single concrete issue label, <=120 chars. "
            "Prefer specific refs such as field, table, sheet, section, or metric names. "
            "Do not explain the issue or suggest a fix."
        )
    )


class NonBlockingIssue(BaseModel):
    type: NonBlockingIssueType = Field(
        description=(
            "Non-blocking issue type: "
            "'benign_omission' = source JSON content omitted because it is outside template scope; "
            "'style_redundancy' = repeated or overly wordy phrasing; "
            "'readability' = unclear, hard to scan, or poorly structured wording."
        )
    )
    item: str = Field(
        description=(
            "Single concrete issue label, <=120 chars. "
            "Prefer specific refs such as field, table, sheet, section, or metric names. "
            "Do not explain the issue or suggest a fix."
        )
    )


class EvalResult(BaseModel):
    blocking_issues: list[BlockingIssue] = Field(
        default_factory=list,
        max_length=10,  # Max length -> focus only on critical issues & reduce output tokens
        description=(
            "Blocking issues that must be fixed before the documentation passes evaluation. "
            "Only include hallucination, critical_omission, or accuracy_error. "
            "Prefer the most important issues first. "
            "Return an empty list if there are no blocking issues."
        ),
    )
    non_blocking_issues: list[NonBlockingIssue] = Field(
        default_factory=list,
        max_length=5,  # Max length -> focus only on important issues & reduce output tokens
        description=(
            "Non-blocking issues for audit/observability only. "
            "Only include benign_omission, style_redundancy, or readability. "
            "Do not include missing required template content here. "
            "Prefer an empty list unless there is a meaningful note."
        ),
    )
    feedback_for_generator: str = Field(
        description=(
            "Short instructions for improving the documentation. "
            "Address only blocking issues. "
            "Do not mention non-blocking issues. "
            "If blocking_issues is empty, return 'No changes needed.' "
            "Keep <=600 chars."
        )
    )

    @property
    def passed(self) -> bool:
        return len(self.blocking_issues) == 0

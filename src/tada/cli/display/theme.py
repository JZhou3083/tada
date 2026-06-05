from tada.graph.status import IssueSeverity, SectionState

SECTION_STATE_STYLE = {
    SectionState.PENDING: "grey50",
    SectionState.GENERATING: "yellow",
    SectionState.EVALUATING: "cyan",
    SectionState.RETRYING: "orange3",
    SectionState.REACHED_RETRY_LIMIT: "yellow3",
    SectionState.FAILED: "red",
    SectionState.DONE: "green",
    SectionState.SKIPPED: "grey50",
}


ISSUE_SEVERITY_STYLE = {
    IssueSeverity.ERROR: "red",
    IssueSeverity.WARNING: "yellow",
    IssueSeverity.INFO: "blue",
}

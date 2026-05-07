from tada.graph.events import SectionState

SECTION_STATE_STYLE = {
    SectionState.PENDING: ("⏳", "grey50"),
    SectionState.GENERATING: ("⚙️ ", "yellow"),
    SectionState.EVALUATING: ("🔍", "cyan"),
    SectionState.RETRYING: ("🔄", "orange3"),
    SectionState.DONE: ("✅", "green"),
}

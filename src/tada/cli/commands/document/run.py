import logging

from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry import trace

from tada.application.document_workbook import (
    DocumentWorkbookRequest,
    DocumentWorkbookRunConfig,
)
from tada.cli.commands.document.inputs import (
    prompt_for_summary_flag,
    resolve_output_arg,
    resolve_sections_arg,
    resolve_workbook_arg,
)
from tada.cli.commands.document.progress import run_document_with_progress
from tada.cli.options import (
    AllSectionsOpt,
    OutputOpt,
    SectionOpt,
    WorkbookOpt,
)
from tada.cli.state import TadaCliState
from tada.observability.otel.observe import observe

tracer = trace.get_tracer(__name__)

logger = logging.getLogger(__name__)


@observe(
    "command.document",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value
    },
)
def run_document(
    cli_state: TadaCliState,
    workbook_path: WorkbookOpt = None,
    output_path: OutputOpt = None,
    sections: SectionOpt = None,
    all_sections: AllSectionsOpt = False,
) -> None:
    """Generate Markdown documentation for a Tableau workbook.

    This function resolves all required inputs, parses the workbook, invokes the
    documentation workflow, and writes the generated documentation to disk.

    If any required inputs are not supplied via CLI options, the user is prompted
    for them interactively.

    Args:
        cli_state: CLI state for the current TaDA execution.
        workbook_path: Path to the Tableau workbook to document.
        output_path: Path where the generated Markdown should be written.
        sections: Specific workbook sections to document.
        all_sections: Whether to document all available workbook sections.
    """
    workbook_path = resolve_workbook_arg(workbook_path)
    output_path = resolve_output_arg(output_path, workbook_path)
    sections = resolve_sections_arg(sections, all_sections)
    run_summary_step = prompt_for_summary_flag()

    request = DocumentWorkbookRequest(
        workbook_path=workbook_path,
        output_path=output_path,
        sections=sections,
        run_summary_step=run_summary_step,
    )

    run_config = DocumentWorkbookRunConfig(
        run_id=cli_state.run_context.info.run_id,
        debug=cli_state.cli_options.debug,
        artifacts_dir=cli_state.run_context.paths.artifacts_dir,
        checkpoints_path=cli_state.run_context.paths.checkpoints_path,
    )

    run_document_with_progress(request, run_config)

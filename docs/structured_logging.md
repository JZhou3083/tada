# Structured Logging Design Guide

## Purpose

This guide defines the structured logging pattern for `tada`.

It should be used by developers and LLM-assisted development to keep logs:
* consistent
* searchable
* easy to correlate across CLI, runtime, LangGraph, GenAI, cost and application layers
* useful for debugging without leaking sensitive data

***

# 1. Event Naming Convention

Use dot-separated event names:

```text
<area>.<thing>.<event>
```

Examples:

```text
genai.request.started
graph.node.completed
run.metadata.updated
app.document_workbook.output.saved
```

## Standard lifecycle verbs

Use past-tense outcome verbs where possible:

```text
started
completed
failed
loaded
saved
parsed
updated
resolved
validated
skipped
cancelled
retrying
```

Prefer:

```text
genai.request.completed
```

over:

```text
genai.request.complete
```

Prefer:

```text
genai.request.failed
```

over:

```text
genai.request.error
```

***

# 2. Top-Level Event Areas

Use these primary namespaces.

```text
cli.*
runtime.*
run.*
app.*
graph.*
genai.*
cost.*
```

## Meaning

### `cli.*`

For command-line parsing, option resolution and interactive prompts.

Examples:

```text
cli.options.resolved
cli.options.validation_failed
cli.prompt.started
cli.prompt.answered
cli.prompt.skipped
cli.prompt.cancelled
```

***

### `runtime.*`

For infrastructure owned by `TadaRuntime`.

Examples:

```text
runtime.initialized
runtime.telemetry.initialized
runtime.cleanup.completed
```

Use `runtime.*` for runtime internals, not the business run itself.

***

### `run.*`

For the lifecycle and metadata of a single Tada run.

Examples:

```text
run.started
run.completed
run.failed
run.cancelled
run.metadata.updated
run.state.loaded
run.state.persisted
```

Prefer:

```text
run.metadata.updated
```

over exposing implementation details like:

```text
run_state_store.updated
```

***

### `app.*`

For application-layer use cases.

Use the specific use-case name after `app`.

Examples:

```text
app.document_workbook.started
app.document_workbook.workbook.parsed
app.document_workbook.workflow.started
app.document_workbook.workflow.completed
app.document_workbook.output.saved
app.document_workbook.completed
app.document_workbook.failed
```

Avoid vague names like:

```text
app.output.saved
app.workbook.parsed
```

because they lose use-case context.

***

### `graph.*`

For LangGraph orchestration.

Examples:

```text
graph.run.started
graph.run.completed
graph.run.failed

graph.node.started
graph.node.completed
graph.node.failed
graph.node.skipped

graph.state.updated
graph.edge.traversed
graph.checkpoint.saved
graph.checkpoint.loaded
```

Use fields for details:

```python
logger.info(
    "graph.node.completed",
    graph_name="documentation_workflow",
    node_name="summarise_dashboard",
    elapsed_seconds=1.42,
)
```

Do not encode node names into the event name.

Avoid:

```text
graph.summarise_dashboard.completed
```

Prefer:

```text
graph.node.completed
```

with:

```text
node_name="summarise_dashboard"
```

***

### `genai.*`

For model gateway calls and response handling.

Standard gateway events:

```text
genai.request.started
genai.request.completed
genai.request.failed
genai.request.retrying

genai.response.empty

genai.usage.missing

genai.structured.parsed
genai.structured.validation_failed
```

Use `genai.*` for the model boundary, even if the implementation lives under `tada.llm.gateway`.

***

### `cost.*`

For token pricing and cost calculation.

Examples:

```text
cost.pricing.loaded
cost.pricing.load_failed
cost.calculation.completed
cost.calculation.failed
```

***

# 3. Current Event Renames

Apply these renames for consistency.

```text
genai.request.complete             -> genai.request.completed
genai.request.error                -> genai.request.failed
genai.request.no_text              -> genai.response.empty
genai.request.no_usage_metadata    -> genai.usage.missing
genai.retry                        -> genai.request.retrying
genai.structured.validation_error  -> genai.structured.validation_failed
cost.pricing.config_loaded         -> cost.pricing.loaded
```

Keep:

```text
genai.request.started
cost.calculation.completed
genai.structured.parsed
```

***

# 4. Event Names Should Describe What Happened

Event names should describe the observable event, not the class or implementation that emitted it.

Prefer:

```text
run.metadata.updated
```

Avoid:

```text
run_state_store.metadata_updated
```

Prefer:

```text
genai.request.retrying
```

Avoid:

```text
tenacity.retry
```

Prefer:

```text
app.document_workbook.output.saved
```

Avoid:

```text
document_workbook.write_text.done
```

***

# 5. Use Fields for Detail

Keep event names stable. Put variable information in structured fields.

Good:

```python
logger.info(
    "graph.node.completed",
    graph_name="documentation_workflow",
    node_name="generate_summary",
    elapsed_seconds=2.31,
)
```

Bad:

```python
logger.info("graph.generate_summary.completed")
```

Good:

```python
logger.info(
    "cli.options.resolved",
    command="document-workbook",
    interactive=True,
    output_format="markdown",
)
```

Bad:

```python
logger.info("cli.document_workbook_markdown_interactive_selected")
```

***

# 6. Recommended Common Fields

Use these fields consistently where relevant.

## Correlation fields

```text
run_id
request_id
trace_id
span_id
thread_id
```

## CLI fields

```text
command
interactive
debug
dry_run
config_source
```

## App fields

```text
workbook_path
output_path
artifacts_dir
section_count
run_summary_step
```

## Graph fields

```text
graph_name
node_name
edge_name
checkpoint_id
elapsed_seconds
```

## GenAI fields

```text
method
model_name
schema
elapsed_seconds
status_code
attempt
wait_seconds
```

## Token and cost fields

Use OpenInference-style fields where possible:

```text
llm.model
llm.response.elapsed_seconds
llm.token_count.total
llm.token_count.input
llm.token_count.output
llm.token_count.cached_input
llm.cost.total_usd
llm.cost.input_usd
llm.cost.output_usd
```

***

# 7. Sensitive Data Rules

Do not log raw prompts, generated content, credentials, environment variables, or full free-text user input by default.

Allowed:

```python
logger.info(
    "genai.structured.validation_failed",
    schema="EvalResult",
    response_preview=response_text[:250],
)
```

Use previews only when needed for debugging, and keep them short.

Avoid:

```python
logger.info("genai.prompt.sent", prompt=full_prompt)
```

Avoid logging secrets such as:

```text
api_key
token
password
credential
authorization
```

***

# 8. Application Use-Case Example

For `document_workbook`, use:

```text
app.document_workbook.started
app.document_workbook.workbook.parsed
app.document_workbook.artifacts.saved
app.document_workbook.workflow.started
app.document_workbook.workflow.completed
app.document_workbook.output.saved
app.document_workbook.completed
app.document_workbook.failed
```

Example:

```python
logger.info(
    "app.document_workbook.started",
    workbook_path=str(request.workbook_path),
    output_path=str(request.output_path),
    section_count=len(request.sections),
    run_id=run_config.run_id,
    debug=run_config.debug,
)
```

When saving output, ensure the correct path is logged:

```python
logger.info(
    "app.document_workbook.output.saved",
    output_path=str(request.output_path),
)
```

Do not log the workbook path as the output path.

***

# 9. GenAI Gateway Example

Use this sequence for a successful text generation:

```text
genai.request.started
cost.calculation.completed
genai.request.completed
```

Example:

```python
log.info(
    "genai.request.started",
    method="generate_text",
    content_type=type(contents).__name__,
    has_config=config is not None,
)
```

On missing text:

```python
log.warning(
    "genai.response.empty",
    elapsed_seconds=elapsed,
)
```

On missing usage metadata:

```python
log.warning(
    "genai.usage.missing",
    elapsed_seconds=elapsed,
)
```

On API failure:

```python
log.error(
    "genai.request.failed",
    error_type=type(exc).__name__,
    error=str(exc),
    status_code=getattr(exc, "code", None),
    elapsed_seconds=elapsed,
)
```

On retry:

```python
logger.warning(
    "genai.request.retrying",
    attempt=retry_state.attempt_number,
    wait_seconds=wait,
    total_idle_seconds=round(retry_state.idle_for, 2),
    error_type=type(exc).__name__ if exc else None,
    error=str(exc) if exc else None,
)
```

On structured parse success:

```python
log.info(
    "genai.structured.parsed",
    model_name=model,
    schema=schema_model.__name__,
)
```

On structured validation failure:

```python
log.error(
    "genai.structured.validation_failed",
    model_name=model,
    schema=schema_model.__name__,
    error_type=type(exc).__name__,
    error=str(exc),
    response_preview=text_response.content[:250],
)
```

***

# 10. Spans and Observability

Span names should follow the same conceptual structure as events, but represent operations rather than moments.

Good span names:

```text
app.document_workbook
genai.generate_text
genai.generate_structured_response
graph.documentation_workflow
```

For the application use case:

```python
@observe(
    "app.document_workbook",
    attributes={
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
    },
)
def document_workbook(...):
    ...
```

The span name identifies the operation. Logs inside the span identify lifecycle events.

***

# 11. Logging Levels

Use levels consistently.

## `info`

Normal lifecycle events.

```text
run.started
graph.node.completed
genai.request.completed
app.document_workbook.output.saved
```

## `warning`

Recoverable or degraded behaviour.

```text
genai.request.retrying
genai.response.empty
genai.usage.missing
cli.prompt.skipped
```

## `error`

Failed operations that raise or prevent completion.

```text
run.failed
graph.node.failed
genai.request.failed
genai.structured.validation_failed
cost.calculation.failed
```

***

# 12. Final Recommended Event Set

Use this as the baseline vocabulary.

```text
cli.options.resolved
cli.options.validation_failed
cli.prompt.started
cli.prompt.answered
cli.prompt.skipped
cli.prompt.cancelled

runtime.initialized
runtime.telemetry.initialized
runtime.cleanup.completed

run.started
run.completed
run.failed
run.cancelled
run.metadata.updated
run.state.loaded
run.state.persisted

app.document_workbook.started
app.document_workbook.workbook.parsed
app.document_workbook.artifacts.saved
app.document_workbook.workflow.started
app.document_workbook.workflow.completed
app.document_workbook.output.saved
app.document_workbook.completed
app.document_workbook.failed

graph.run.started
graph.run.completed
graph.run.failed
graph.node.started
graph.node.completed
graph.node.failed
graph.node.skipped
graph.state.updated
graph.edge.traversed
graph.checkpoint.saved
graph.checkpoint.loaded

genai.request.started
genai.request.completed
genai.request.failed
genai.request.retrying
genai.response.empty
genai.usage.missing
genai.structured.parsed
genai.structured.validation_failed

cost.pricing.loaded
cost.pricing.load_failed
cost.calculation.completed
cost.calculation.failed
```

***

# 13. Rules for Future Development

When adding a new log event:

1. Choose an existing top-level area.

2. Use the pattern:

   ```text
   <area>.<thing>.<event>
   ```

3. Use a stable event name.

4. Put variable details in fields.

5. Prefer lifecycle verbs:

   ```text
   started
   completed
   failed
   saved
   loaded
   parsed
   updated
   skipped
   cancelled
   retrying
   ```

6. Do not include class names unless the class is the domain concept.

7. Do not log raw prompts, generated documents, secrets, or large payloads.

8. Include correlation fields where available.

9. Use `failed` for errors that stop the operation.

10. Keep event names boring, predictable and searchable.

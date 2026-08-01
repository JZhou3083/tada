# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Tableau Metadata Agent (TaDA) — an LLM-driven CLI that generates standardised Markdown documentation for Tableau workbooks (`.twb`/`.twbx`). Core design principle: **deterministic metadata extraction (XML parsing) is strictly separated from probabilistic language generation (LLM)** — the extraction pipeline must produce structured, inspectable intermediate representations, and the LLM is only used for summarisation/explanation/formatting, not for inferring hidden structure. See `DESIGN.md` for the full architecture rationale and end-to-end runtime flow.

## Commands

Environment setup uses `uv` (or `pip` as a fallback):

```shell
uv sync                        # install dependencies
uv run pip install -e .        # install CLI entrypoints (`tada`, `tada-trace-viewer`) locally
cp .env.example .env            # copy env var template (gitignored, do not commit)
uv run pre-commit install       # install pre-commit + commit-msg hooks (required for contributing)
```

Running the CLI:

```shell
tada document                                  # main documentation workflow
tada                                            # interactive fallback menu
tada document --workbook my_workbook.twb --output documentation.md --all-sections
tada --debug document                           # debug mode: console logs + prints artifact locations
python tada-cli.py                              # run without installing the package
tada-trace-viewer                               # launch local Arize Phoenix trace viewer (needs `uv sync --extra trace-viewer`)
```

Tests:

```shell
uv run pytest                              # run all tests
uv run pytest tests/observability/test_cost_calculators.py   # single file
uv run pytest tests/observability/test_cost_calculators.py::test_name  # single test
uv run pytest -m unit                      # only unit tests
uv run pytest -m integration               # only tests using packaged files / multiple components
```

Lint/format (via pre-commit, using `ruff`):

```shell
uv run pre-commit run              # run configured hooks on staged files
uv run pre-commit run --all-files  # run against the whole repo
```

Commits must follow Conventional Commits (enforced by `commitlint` via pre-commit's `commit-msg` hook). Use `uv run cz commit` (or `uv run cz c`) for a guided commit message, or write conventional commits (`feat:`, `fix:`, `chore:`, `revert:`, etc.) directly.

## Configuration

Settings are managed via `pydantic-settings` in `src/tada/settings.py`, loaded from environment variables prefixed `TADA_` and/or a local `.env` file (see `.env.example`). Key settings:

- `TADA_STATE_DIR` — local runtime state root (traces, checkpoints, run metadata); defaults to the OS app-state dir.
- `TADA_CLIENT_PROJECT` / `TADA_CLIENT_LOCATION` — GCP project/location used to construct the Vertex AI GenAI client.
- `TADA_GRAPH__SECTION_DOCUMENTER__*` and `TADA_GRAPH__WORKBOOK_DOCUMENTER__*` — nested graph settings (e.g. `DOCUMENTATION_MODEL`, `EVALUATION_MODEL`, `MAX_DOCUMENTATION_RETRIES`, `SUMMARY_MODEL`), double-underscore-delimited for nested config.

`get_settings()` is `lru_cache`d — settings are effectively singletons per process.

## Architecture

The codebase (`src/tada/`) is a layered application, invoked top-down as: CLI → application → tableau extraction + graph orchestration → LLM gateway → observability.

- **`cli/`** — Typer app (`cli/app.py`), commands (`cli/commands/`), interactive menu/prompting (`cli/menu.py`, `cli/prompting.py`), and Rich-based display (`cli/display/`). `main()` builds a `RunContext`, wraps execution in `TadaRuntime` (tracing lifecycle), then runs the Typer app.
- **`application/`** — use-case orchestration independent of the CLI. `document_workbook.py` is the primary entrypoint: parses the workbook, builds and runs the workbook-documenter graph, and writes the final Markdown. `graph_runner.py` wraps graph invocation to stream `GraphStatusEvent`s to a `StatusSink` (e.g. for live CLI progress). `ports.py` defines the `StatusSink` protocol.
- **`domain/`** — core concepts: `Workbook` (parsed, frozen Pydantic model built via `Workbook.from_file`) and `WorkbookSection` (`StrEnum` of `datasources`, `calculations`, `dashboards`, `worksheets`, `actions`, `parameters`, `tables` — each knows how to `fetch_from` a `Workbook`).
- **`tableau/`** — deterministic extraction layer. `loader.py` loads workbook XML; `xml/prune.py` and `xml/select.py` drop/select XPaths (e.g. removing `//external`, `//thumbnails` before extraction); `extractors.py` produces the structured dict per section; `xml/serialize.py`/`xml/tags.py` are XML helpers. A PII-scan step is planned but not yet implemented here (see `TODO` in `domain/workbook.py`).
- **`graph/`** — LangGraph-based orchestration, split into two nested compiled graphs:
  - **`workbook_documenter/`** — top-level graph. Fans out to one `section_documenter` subgraph invocation per requested `WorkbookSection` (via `routing.route_plan_to_documenters`), then summarises all section docs and assembles final Markdown.
  - **`section_documenter/`** — per-section subgraph: `prepare_section` (skip if no data) → `generate_section_documentation` (LLM call using section-specific prompt + response template from `prompts/sections/`) → `evaluate_section_documentation` (structured LLM eval against `EvalResult` schema) → routes to `emit` / `emit_with_issues` / `retry` based on eval result and `max_documentation_retries`.
  - Each graph has its own `context.py` (LangGraph `context_schema`, e.g. carrying the LLM gateway + settings), `state.py` (state/input/output schemas), `ids.py` (node id enums), and `settings.py` (Pydantic settings for models/retries).
  - `status.py`/`status_stream.py` define a side-channel status/progress model (`GraphStatusEvent`, `SectionState`, `StatusIssue`, `LLMUsage`) emitted via LangGraph's stream writer during node execution — this is how the CLI shows live per-section progress, retries, issues, and running token/cost totals independent of the graph's actual state.
- **`llm/`** — provider-agnostic gateway. `gateway/base.py` defines the `LLMGateway` `Protocol` (`generate_text` / `generate_structured_response`) and the shared `validate_structured_payload()` helper; `gateway/providers/` has one adapter per backend — `google_vertex.py` (`GoogleVertexGateway`), `openai_compatible.py` (`OpenAIGateway`, used for both OpenAI and DeepSeek), `anthropic.py` (`AnthropicGateway`, using forced tool-use since Anthropic has no JSON mode). `gateway/factory.py`'s `get_gateway()` is an `lru_cache`d singleton that dispatches on `settings.llm_provider` (`TADA_LLM_PROVIDER`: `google_vertex` / `openai` / `anthropic` / `deepseek`). `gateway/retries.py`'s `with_retry(is_retryable)` factory holds the shared tenacity backoff policy; each provider supplies its own rate-limit predicate. `configs.py`'s `GenerationConfig` is a provider-neutral dataclass (temperature/top_p/seed/max_output_tokens/system_instruction/labels) that each adapter translates into its own SDK's request shape. `schemas.py` holds shared LLM response schemas (e.g. `EvalResult`).
- **`observability/`** — cross-cutting. `logging.py` configures `structlog`; `otel/observe.py` provides the `@observe(...)` decorator used to wrap functions/nodes in OpenInference-tagged OpenTelemetry spans (see usage throughout `graph/` and `application/`); `otel/jsonl_exporter.py` exports spans to a local JSONL file per run; `cost/` calculates USD cost from token usage against a pricing config (`safe_calculate_cost` returns `CostSuccess`/`CostFailure` rather than raising).
- **`prompts/`** — Markdown prompt/template assets, loaded via `importlib.resources` in `prompts/loader.py` (`load_prompt(name)` for top-level prompts like `system.md`/`evaluation.md`/`summariser.md`; `load_section_documentation_prompts(section)` for the paired `sections/{section}.prompt.md` + `sections/{section}.response_template.md`). These are packaged data (see `pyproject.toml` `[tool.hatch.build...] include`), not just dev-time files.
- **`runtime/`** — per-invocation plumbing independent of LLM/graph concerns. `context.py`'s `RunContext` generates a run ID and lays out per-run paths (`run.json`, `app.log`, `traces.jsonl`, `checkpoints.db`, `artifacts/`) under `state_dir/runs/<run_id>/`. `lifecycle.py`'s `TadaRuntime` is a context manager owning the OpenTelemetry `TracerProvider`, the JSONL span exporter/processor, GenAI auto-instrumentation, and run-state (`running`/`completed`/`failed`) persistence — used once around the whole CLI invocation in `cli/app.py:main()`.
- **`trace_viewer/`** — separate, optional tool (`tada-trace-viewer` entrypoint) that loads previously exported JSONL traces into a local Arize Phoenix server for inspection (retries, evaluations, intermediate generations). Requires the `trace-viewer` extra (`arize-phoenix`, `pandas`); `_optional.py` guards these optional imports.

### Adding a new workbook section type

Touches multiple layers: `domain/sections.py` (enum member), `tableau/extractors.py` (extraction logic), `prompts/sections/` (new `.prompt.md` + `.response_template.md` pair), and whatever routes sections into the workbook-documenter graph (`graph/workbook_documenter/routing.py`, `payload.py`).

### Adding/changing an LLM call

Goes through `llm/gateway`'s `LLMGateway` Protocol (`generate_text` / `generate_structured_response`), obtained via `get_gateway()` — do not call a provider SDK directly from graph nodes, since the gateway adapter is what wires in retries, usage normalisation, cost calculation, and telemetry. Adding a new provider means adding an adapter under `gateway/providers/` and a case in `gateway/factory.py:get_gateway()`, not touching graph nodes.

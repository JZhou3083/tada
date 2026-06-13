# Design Doc: Tableau Meta Agent
 
# 1. Context
 
Tableau Metadata Agent is an LLM-driven CLI tool that genertes standardised documentation for Tableau workbooks.
 
The project exisits to reduce the manual effort of documenting Tableau assets, improve consistency of generated documentation, and support onboarding, matainability, and govenance for analytics developers. Internal project materials describes the core problem as manual dashboard/workbook documentation being inconsistent, time-consuming, and often neglected, leading to knowledge gaps and reduced auditability.
 
The current product surface is a developer-facing CLI:
- 'tada document'
- interactive prompting when required arguments are missing
- local observability artifacts (logs + OpenTelemetry traces)
- optional trace viewing via local Arize Phoenix integration
 
## 2. Problem Statement
 
Analytics developers often inherit Tableau workbooks without clear document of:
- data source
- worksheets
- dashboards
- parameters
- calculations
- actions
- structural relationship
 
This results in slow onboarding, knowledge silos, and weak governance. Internal discovery material states that the desired solution is to extract workbook metadata (TWB/XML and potentially API-based metadata) and transform it into clear, standardised documentation. 
## 3. Goals
 
### Primary goals
1. Genreatte consistent Markdown documentation for Tableau workbooks.
2. Provide  a usable local CLI workflow for analytics developers.
3. Make generation observable through los, traces, retries, and artifacts.
4. Create a modular pipeline so extraction, prompting, generation, and output rendering can evolve independantly.
 
### Secondary goals
1. Support debugging and evaluation of intermediate LLM steps.
2. Provide a foundation for future extensions such as richer outputs, diagrams, and platform integration.
 
## 4. Non-goals
 
The following are explicitly out of scope for the current phase:
- Fully managed server-hosted SaaS deployment
- Editing and mutating of the Tableau workbooks
- Real-time collaborative editing of generated documentation
- Broad enterprise-wide access management
- Strong gurantees of semantic correctness beyond source metadata quality
 
This is consistent with the current positioning of the tool as a CLI-first workflow and with internal dicussions that stil treat packaging, access scopr, and pilot usage as evolving concerns.
 
## 5. Users
 
### Primary user
Analytics developer / Tableau creator who wants to generate documentation for an existing workbook.
 
### Core user job
 
“Given a Tableau workbook, generate a readable, standardised documentation artifact with minimal manual effort.”
 
Internal project materials describe similar user stories focused on onboarding, automatically documenting workbook logic, and reducing manual documentation overhead. 
 
## 6. High-Level Architecture
 
The system is organised as a layered local application with the following responsibilities:
 
### 6.1 Interface Layer
- `cli/`
- Handles command registration, user input, prompting, progress display, and debug mode.
 
### 6.2 Application Layer
- `application/`
- Coordinates the document workflow through use-case level orchestration.
- Encapsulates the “document workbook” operation independent from CLI specifics.
 
### 6.3 Domain Layer
- `domain/`
- Defines core business concepts such as workbook and documentation sections.
 
### 6.4 Processing / Orchestration Layer
- `graph/`
- Encodes the documentation workflow as graph-based execution.
- Splits responsibilities into:
  - workbook-level orchestration
  - section-level documentation
- Includes routing, state, context, payload, schemas, and markdown assembly.
 
### 6.5 Tableau Extraction Layer
- `tableau/`
- Parses Tableau workbook inputs and extracts structured metadata.
- Includes XML-specific selection, pruning, and serialisation helpers.
 
### 6.6 LLM Gateway Layer
- `llm/`
- Encapsulates model invocation, retries, normalisation, schemas, and telemetry hooks.
 
### 6.7 Observability Layer
- `observability/`
- Cross-cutting support for logging, cost calculation, and OpenTelemetry export.
 
### 6.8 Operations Tooling
- `trace_viewer/`
- Independent local tooling to load past traces into Phoenix for debugging and inspection.
 
## 7. Key Design Principle
 
The core design principle is:
 
> Separate deterministic metadata extraction from probabilistic language generation.
 
The extraction pipeline should produce structured, inspectable intermediate representations from Tableau inputs. LLM usage should focus on summarisation, explanation, and formatting rather than guessing hidden structure.
 
This principle is reinforced by internal merge-request discussion where prompt architecture was simplified and more structure was shifted into extraction/template layers. 
 
## 8. End-to-End Runtime Flow
 
1. User invokes `tada document` from CLI.
2. CLI resolves inputs from flags or interactive prompts.
3. Application layer creates runtime context and launches the workbook document workflow.
4. Tableau extraction layer loads the workbook and produces structured metadata.
5. Workbook-level graph determines which sections to document.
6. For each section:
   - build section context
   - load prompt/template assets
   - invoke LLM gateway
   - normalise/validate outputs
   - render markdown
7. Workbook-level graph assembles final documentation output.
8. Observability layer emits:
   - logs
   - traces
   - token/cost metadata where available
9. Output markdown is written to target path.
10. Optional: user launches trace viewer to inspect previous runs.
 
## 9. Data Flow
 
### Input
- Tableau workbook file (`.twb`, possibly `.twbx`)
- CLI arguments / interactive inputs
- prompt templates and response templates from `prompts/`
 
### Intermediate artifacts
- extracted tableau metadata
- section-level context/state
- LLM requests and responses
- run metadata, logs, traces, cost records
 
### Output
- final Markdown documentation
- local observability artifacts
- trace viewer-compatible telemetry artifacts
 
## 10. Operational Concerns
 
### 10.1 Observability
Observability is a first-class concern in this system rather than an afterthought. The README already exposes logs, OpenTelemetry traces, debug mode, and a local trace viewer. Internal discussions also mention the need to improve retry tracking, cost logging, and visibility once the CLI is distributed more broadly.

### 10.2 Reliability
Expected failure modes include:
- invalid workbook input
- XML schema variation
- partial metadata extraction failures
- LLM retries / timeout / malformed output
- cost spikes on large or complex workbooks
- output rendering mismatch against template expectations
 
Internal scrum notes explicitly mention improving retry tracking, reducing worksheet retries via input cleaning, and concern about large workbooks driving unexpected cost. 
 
### 10.3 Privacy
PII/privacy is a key system concern. Internal project documents and meeting notes both state that workbook metadata may contain sensitive values in fields, calculations, descriptions, or paths, and current thinking emphasises redaction as early as possible in the XML pipeline to avoid propagating sensitive content into JSON artifacts, logs, or LLM requests. 
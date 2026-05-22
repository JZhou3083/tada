---
document: "Dashboard Documentation"
version: "v1.1.0"
required_sections:
 - Dashboard Overview
 - Layout Summary
ai_settings:
 todo_token: "TODO"
 missing_field_behavior: "insert_todo"
processing:
 strip_blocks:
  - { start: "@@DEVELOPER_NOTES_START", end: "@@DEVELOPER_NOTES_END" }
 content_window:
  - { start: "@@TEMPLATE_START", end: "@@TEMPLATE_END" }
---

@@DEVELOPER_NOTES_START
Purpose
- This template produces documentation for each Tableau dashboard.
- It focuses on objects that developers and users actively recognise and interact with.

Rules
- Never introduce fields not present in the JSON.
- Object names and references must be taken verbatim from the JSON.
- Only the "Dashboard Overview" and "Layout Summary" sections are AI-generated.
- All other sections are strictly declarative.
- Do not document Tableau layout containers or internal structure.


Output
- Valid Markdown only.
- No developer notes in the final output.
@@DEVELOPER_NOTES_END

@@TEMPLATE_START
# Dashboard Documentation
<!-- ai:section=tableau_dashboard_documentation, expect="text" -->

{{#each dashboards}}

## Dashboard: {{name}}
<!-- ai:section=dashboard_name, expect="text" -->

## Dashboard Overview
<!-- ai:section=dashboard_overview, expect="text" -->
{{dashboard_summary}}

## Layout Summary
<!-- ai:section=dashboard_layout_summary, expect="text" -->
{{layout_description}}

{{#if zones.zone}}

{{!-- ============================ --}}
{{!-- Worksheets --}}
{{!-- ============================ --}}
{{#each zones.zone}}
 {{#if name}}
  {{#unless type-v2}}
## Worksheets
<!-- ai:section=worksheets, expect="list" -->
{{#each ../../zones.zone}}
 {{#if name}}
  {{#unless type-v2}}
- {{name}}
  {{/unless}}
 {{/if}}
{{/each}}
{{break}}
  {{/unless}}
 {{/if}}
{{/each}}

{{!-- ============================ --}}
{{!-- Filters --}}
{{!-- ============================ --}}
{{#each zones.zone}}
 {{#if (eq type-v2 "filter")}}
## Visible Filters
<!-- ai:section=filters, expect="list" -->
{{#each ../../zones.zone}}
 {{#if (eq type-v2 "filter")}}
- Filter attributed to {{name}}
  - Field: {{field_name}}
  - Mode: {{mode}}
 {{/if}}
{{/each}}
{{break}}
 {{/if}}
{{/each}}

{{!-- ============================ --}}
{{!-- Parameter Controls --}}
{{!-- ============================ --}}
{{#each zones.zone}}
 {{#if (eq type-v2 "paramctrl")}}
## Visible Parameter Controls
<!-- ai:section=parameters, expect="list" -->
{{#each ../../zones.zone}}
 {{#if (eq type-v2 "paramctrl")}}
- {{#if formatted-text.run.#text}}{{formatted-text.run.#text}} ({{zone.param}}){{else}}{{zone.param}}{{/if}}
  - Control Type: {{mode}}
 {{/if}}
{{/each}}
{{break}}
 {{/if}}
{{/each}}

{{!-- ============================ --}}
{{!-- Text --}}
{{!-- ============================ --}}
{{#each zones.zone}}
 {{#if (eq type-v2 "text")}}
## Text
<!-- ai:section=text, expect="list" -->
{{#each ../../zones.zone}}
 {{#if (eq type-v2 "text")}}
- {{#each formatted-text.run}}{{#unless (eq #text "Æ")}}{{#text}} {{/unless}}{{/each}}
 {{/if}}
{{/each}}
{{break}}
 {{/if}}
{{/each}}

{{!-- ============================ --}}
{{!-- Dashboard Controls --}}
{{!-- ============================ --}}
{{#each zones.zone}}
 {{#if (eq type-v2 "dashboard-object")}}
  {{#unless url}}
## Dashboard Controls
<!-- ai:section=dashboard_controls, expect="list" -->
{{#each ../../zones.zone}}
 {{#if (eq type-v2 "dashboard-object")}}
  {{#unless url}}
- {{summarise_control resolving zone ids to names}}
  {{/unless}}
 {{/if}}
{{/each}}
{{break}}
  {{/unless}}
 {{/if}}
{{/each}}

{{!-- ============================ --}}
{{!-- Legends --}}
{{!-- ============================ --}}
{{#each zones.zone}}
 {{#if (or (eq type-v2 "color") (eq type-v2 "size") (eq type-v2 "shape"))}}
## Visible Legends
<!-- ai:section=legends, expect="list" -->
{{#each ../../zones.zone}}
 {{#if (eq type-v2 "color")}}
- Color legend: {{resolved_field_name}}
 {{/if}}
 {{#if (eq type-v2 "size")}}
- Size legend: {{resolved_field_name}}
 {{/if}}
 {{#if (eq type-v2 "shape")}}
- Shape legend: {{resolved_field_name}}
 {{/if}}
{{/each}}
{{break}}
 {{/if}}
{{/each}}

{{!-- ============================ --}}
{{!-- Images --}}
{{!-- ============================ --}}
{{#each zones.zone}}
 {{#if (eq type-v2 "bitmap")}}
## Images
<!-- ai:section=images, expect="list" -->
{{#each ../../zones.zone}}
 {{#if (eq type-v2 "bitmap")}}
- {{param}}
 {{/if}}
{{/each}}
{{break}}
 {{/if}}
{{/each}}

{{!-- ============================ --}}
{{!-- Web Pages --}}
{{!-- ============================ --}}
{{#each zones.zone}}
 {{#if url}}
## Web Pages
<!-- ai:section=web_pages, expect="list" -->
{{#each ../../zones.zone}}
 {{#if url}}
- {{url}}
 {{/if}}
{{/each}}
{{break}}
 {{/if}}
{{/each}}

{{/if}}

---
{{/each}}

@@TEMPLATE_END

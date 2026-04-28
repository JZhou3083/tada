---
document: "Actions Documentation"
version: "v1.0.0"

required_sections:
  - Workbook Overview
  - Dashboard Interaction Summary
  - Action Types

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
- This file defines the template for generating Tableau action documentation.
- Only values inside the TEMPLATE block should be populated.

Rules for generation
- Never add fields that do not appear in the source JSON. If a value is missing, the conditional blocks will naturally omit it.
- Never modify, reorder, or remove Handlebars control structures such as #if, #each, or comments.
- Do not include these developer notes in the final output.

Output Requirements
- Do not include developer notes in the final output when the template is executed.
- Output must be valid Markdown since the document is intended for human-readable technical documentation.
- Avoid adding interpretation or commentary. The output should be purely factual and based on supplied values.

@@DEVELOPER_NOTES_END

@@TEMPLATE_START
# Actions Documentation
<!-- ai:section=tableau_actions_documentation_template, expect="text" -->

## 1. Workbook Overview
<!-- ai:section=workbook_overview, expect="text" -->
**Workbook Name:** {{workbook_name}}

---

## 2. Dashboard Interaction Summary
<!-- ai:section=dashboard_interaction_summary, expect="text" -->

{{#each dashboards}}
### Dashboard: {{dashboard_name}}
<!-- ai:section=dashboard_name, expect="text" -->

**Summary:**
<!-- ai:section=dashboard_interaction_summary_text, expect="text" -->

**Action Counts:**
<!-- ai:section=action_counts, expect="table", keys="action_type,count" -->
{{#if action_counts}}
{{#each action_counts}}
- {{@key}}: {{this}}
{{/each}}
{{else}}
{{#if actions.filter}}- filter: {{actions.filter.length}}{{/if}}
{{#if actions.highlight}}- highlight: {{actions.highlight.length}}{{/if}}
{{#if actions.url}}- url: {{actions.url.length}}{{/if}}
{{#if actions.parameter}}- parameter: {{actions.parameter.length}}{{/if}}
{{#if actions.set}}- set: {{actions.set.length}}{{/if}}
{{#if actions.goto_sheet}}- goto_sheet: {{actions.goto_sheet.length}}{{/if}}
{{/if}}

---

## Filter Actions
<!-- ai:section=filter_actions, expect="text" -->
{{#if actions.filter}}
{{#each actions.filter}}

### Filter Action: {{caption}}
<!-- ai:section=filter_action, expect="text" -->
- **Purpose:** {{purpose}}
- **Source Worksheet:** {{source_worksheet}}
- **Target Dashboard:** {{target_dashboard}}
- **Activation Type:** {{activation_type}}
- **Auto Clear:** {{auto_clear}}
- **Filter Parameters:**
{{#if filter_params}}
{{#each filter_params}}
  - {{name}}: {{value}}
{{/each}}
{{else}}
  - None
{{/if}}

---
{{/each}}
{{/if}}

## Highlight Actions
<!-- ai:section=highlight_actions, expect="text" -->
{{#if actions.highlight}}
{{#each actions.highlight}}

### Highlight Action: {{caption}}
<!-- ai:section=highlight_action, expect="text" -->
- **Purpose:** {{purpose}}
- **Source Worksheet:** {{source_worksheet}}
- **Fields Highlighted:**
{{#if highlight_fields}}
{{#each highlight_fields}}
  - {{field_name}}
{{/each}}
{{else}}
  - None
{{/if}}

---
{{/each}}
{{/if}}

## URL Actions
<!-- ai:section=url_actions, expect="text" -->
{{#if actions.url}}
{{#each actions.url}}

### URL Action: {{caption}}
<!-- ai:section=url_action, expect="text" -->
- **Purpose:** {{purpose}}
- **Source Worksheet:** {{source_worksheet}}
- **URL:** {{url}}
- **Open In:** {{open_target}}

---
{{/each}}
{{/if}}

## Parameter Actions
<!-- ai:section=parameter_actions, expect="text" -->
{{#if actions.parameter}}
{{#each actions.parameter}}

### Parameter Action: {{caption}}
<!-- ai:section=parameter_action, expect="text" -->
- **Purpose:** {{purpose}}
- **Source Worksheet:** {{source_worksheet}}
- **Parameter Updated:** {{target_parameter}}
- **Source Field:** {{source_field}}
- **Activation Type:** {{activation_type}}
- **Clear Option:** {{clear_option}}

---
{{/each}}
{{/if}}

## Set Actions
<!-- ai:section=set_actions, expect="text" -->
{{#if actions.set}}
{{#each actions.set}}

### Set Action: {{caption}}
<!-- ai:section=set_action, expect="text" -->
- **Purpose:** {{purpose}}
- **Source Worksheet:** {{source_worksheet}}
- **Set Updated:** {{set_name}}
- **Source Field:** {{source_field}}
- **Operation Mode:** {{operation}}

---
{{/each}}
{{/if}}

## Go To Sheet Actions
<!-- ai:section=goto_sheet_actions, expect="text" -->
{{#if actions.goto_sheet}}
{{#each actions.goto_sheet}}

### Go To Sheet Action: {{caption}}
<!-- ai:section=goto_sheet_action, expect="text" -->
- **Purpose:** {{purpose}}
- **Source Worksheet:** {{source_worksheet}}
- **Target Sheet or Dashboard:** {{target_sheet}}

---
{{/each}}
{{/if}}

{{/each}}
@@TEMPLATE_END

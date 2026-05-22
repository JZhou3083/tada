---
document: "Worksheet Documentation"
version: "v1.0.0"

required_sections:
  - Summary
  - Datasources
  - Filters
  - Columns
  - Rows
  - Marks
  - Tooltips

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
- This template documents each Tableau worksheet extracted from the workbook JSON.

Rules
- Datasources: read from `table.view.datasources.datasource`.
- Rows shelf: `table.rows["#text"]` OR empty.
- Columns shelf: `table.cols["#text"]` OR empty.
- Filters:
- Marks: iterate through `table.panes.pane` (or array) and collect:
    - mark type (Bar/Shape/Line/Text/etc.)
    - encodings: color, size, shape, text, tooltip (ignore tooltip), and any others
- Only the worksheet description paragraph is AI-generated.

Output
- Only markdown.
- Never output developer notes
- Never output AI markers (<!-- ai:section= -->)
- ALWAYS resolve internal names to user friendly names
   `examples: `
    `[federated.0zuz1tw1xgbavv1es02u90unkpyw].[none:channel:nk] resolves to '[Channel]'`
    `[federated.0zuz1tw1xgbavv1es02u90unkpyw].[tdy:event_date:qk] resolves to [DAY(Event Date)]`

@@DEVELOPER_NOTES_END

@@TEMPLATE_START

# Tableau Worksheets Documentation

{{#each worksheets}}
### Worksheet: {{name}}

### Summary
<!-- ai:section=summary, expect="text" -->
{{worksheet_description}}

### Datasources
<!-- ai:section=datasources, expect="table" -->
  {{#if table.view.datasources.datasource}}

  | Datasource |
  |-----------|
  {{#each table.view.datasources.datasource}}
  | {{#if caption}}{{caption}}{{else}}{{name}}{{/if}} |
  {{/each}}

  {{/if}}

---

### Filters
<!-- ai:section=filters, expect="list" -->
  {{#if filter}}

  {{#each filter}}
  - Field: {{field}}
    - Selection: {{#each filter[*].groupfilter.member | filter[*].groupfilter.groupfilter[*].member else All}}
  {{/each}}

  {{/if}}

### Columns Shelf
<!-- ai:section=columns, expect="string" -->
  {{#if table.cols}}
  `{{table.cols.#text}}`
  {{else}}
  None
  {{/if}}


### Rows Shelf
<!-- ai:section=rows, expect="string" -->
  {{#if table.rows}}
  `{{table.rows.#text}}`
  {{else}}
  None
  {{/if}}

### Marks
<!-- ai:section=marks, expect="text" -->
{{#if table.panes.pane}}
{{#each table.panes.pane}}

#### {{x-axis-name | y-axis-name else }} {{#if x-axis-name | y-axis-name}}{{(id)}}{{/if}}
  - Mark Type: {{mark.class}}
  {{#if encodings.color}}
  {{#each encodings.color}}
  - Color: {{encodings.color}}
  {{/each}}{{/if}}
  {{#if encodings.size}}
  {{#each encodings.size}}
  - Size: {{encodings.size}}
  {{/each}}{{/if}}
  {{#if encodings.shape}}
  {{#each encodings.shape}}
  - Shape: {{encodings.shape}}
  {{/each}}{{/if}}
  {{#if encodings.text}}
  {{#each encodings.text}}
  - Text: {{encodings.text}}
  {{/each}}{{/if}}
  {{#if encodings.detail}}
  {{#each encodings.detail}}
  - Detail: {{encodings.detail}}
  {{/each}}{{/if}}
  {{#if encodings.label}}
  {{#each encodings.label}}
  - Label: {{encodings.label}}
  {{/each}}{{/if}}

{{/each}}
{{/if}}

### Analytics Pane Objects (Reference Lines, etc)
<!-- ai:section=analytics_objects, expect="list" -->
{{#if analytics_pane}}
  {{#each analytics_pane}}
  - Type: {{type}}
  - Field: {{field}}
  - Scope: {{scope}}
  - Computation: {{computation}}
  {{/each}}
{{/if}}

### Tooltips
<!-- ai:section=tooltips, expect="text" -->
  Tooltip Type: {{custom | automatic | none}}

  {{tooltip_summary}}

---
---

{{/each}}
@@TEMPLATE_END

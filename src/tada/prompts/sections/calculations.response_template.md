---
document: "Calculations Documentation"
version: "v1.0.0"

required_sections:
  - Calculated Fields

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
- This file defines the template for generating Tableau calculations documentation.

Rules for generation
- Except for the `description` column, never add fields that do not appear in the source JSON.
- The `description` column is the only AI‑generated field and must be a single line per row (see prompt).
- Do not modify, reorder, or remove Handlebars control structures such as #if, #each, or comments.
- Do not include these developer notes in the final output.

Output Requirements
- Output must be valid Markdown.
- Avoid interpretation beyond the one‑line description; keep it strictly grounded in the formula text.
- Preserve whitespace in formulas as they appear in the source JSON (no reformatting).
- If a required value is absent in the JSON, output the literal string "None".

Data Shape
- Calculations may come as:
  1) an object at the root (keys are calc identifiers; values are calc objects), or
  2) an array under `calculations`.
- The template handles both. Maintain the original ordering as presented in the input.

@@DEVELOPER_NOTES_END

@@TEMPLATE_START
#  Calculations Documentation
<!-- ai:section=tableau_calculations_documentation_template, expect="text" -->

## Calculated Fields Summary
<!-- ai:section=calculated_fields_summary, expect="text" -->

## Calculated Fields
<!-- ai:section=calculated_fields, expect="table", keys="Caption,datatype,name,role,formula,description", purpose="List all calculated fields with an AI-generated one-line description derived from the formula." -->

{{#if calculations}}
| Caption | datatype | name | role | formula | description |
|---|---|---|---|---|---|
{{#each calculations}}
| {{#if caption}}{{caption}}{{else}}None{{/if}} | {{#if datatype}}{{datatype}}{{else}}None{{/if}} | {{#if name}}{{name}}{{else}}None{{/if}} | {{#if role}}{{role}}{{else}}None{{/if}} | {{#if calculation.formula}}{{calculation.formula}}{{else}}None{{/if}} | {{#if description}}{{description}}{{else}}None{{/if}} |
{{/each}}
{{else}}
{{!-- Fallback when calculations are provided as a root-level object --}}
{{#if .}}
| Caption | datatype | name | role | formula | description |
|---|---|---|---|---|---|
{{#each .}}
| {{#if caption}}{{caption}}{{else}}None{{/if}} | {{#if datatype}}{{datatype}}{{else}}None{{/if}} | {{#if name}}{{name}}{{else}}None{{/if}} | {{#if role}}{{role}}{{else}}None{{/if}} | {{#if calculation.formula}}{{calculation.formula}}{{else}}None{{/if}} | {{#if description}}{{description}}{{else}}None{{/if}} |
{{/each}}
{{else}}
_No calculated fields found._
{{/if}}
{{/if}}

@@TEMPLATE_END

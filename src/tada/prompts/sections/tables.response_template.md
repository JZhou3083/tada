---
document: "Tables Documentation"
version: "v1.0.0"

required_sections:
  - Tables
  - Columns

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
- This file defines the template for generating Tableau parameter documentation.
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
# Tableau Tables Documentation Template
<!-- ai:section=tableau_tables_documentation_template, expect="text" -->

**Table Counts:**
<!-- ai:section=table_counts, expect="table", keys="table_type,count" -->
{{#if table_counts}}
{{#each table_counts}}
- {{@key}}: {{this}}
{{/each}}
{{/if}}

---

## Tables
<!-- ai:section=tables, expect="text" -->
{{#if tables}}
{{#each tables}}

### {{name}}
<!-- ai:section=table, expect="text" -->
- **Purpose:** {{purpose}}
- **Connection** {{connection}}
- **Grid Origin** {{gridOrigin}}
#### **Columns**
{{#if columns}}
| name | datatype | description |
|---|---|---|
{{#each columns}}
| {{#if name}}{{name}}{{else}}None{{/if}} | {{#if datatype}}{{datatype}}{{else}}None{{/if}} | {{#if description}}{{description}}{{else}}None{{/if}} |
{{/each}}
{{/if}}

---
{{/each}}
{{/if}}

{{/each}}
@@TEMPLATE_END

---
document: "Parameters Documentation"
version: "v1.0.0"

required_sections:
  - Parameter Counts
  - Parameters

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
# Tableau Parameters Documentation Template
<!-- ai:section=tableau_parameters_documentation_template, expect="text" -->

**Parameter Counts:**
<!-- ai:section=parameter_counts, expect="table", keys="parameter_type,count" -->
{{#if parameter_counts}}
{{#each parameter_counts}}
- {{@key}}: {{this}}
{{/each}}
{{/if}}

---

## Parameters
<!-- ai:section=parameters, expect="text" -->
{{#if parameters}}
{{#each parameters}}

### Parameter {{caption}}
<!-- ai:section=parameter, expect="text" -->
- **Purpose:** {{purpose}}
- **Datatype** {{datatype}}
- **Name** {{name}}
- **Param Domain Type** {{param-domain-type}}
- **Role** {{role}}
- **Type** {{type}}
- **Default Value** {{value}}
- **Members**
{{#if member}}
{{#each}}
- value: {{value}}
{{#if alias}} - alias:{{alias}} {{/if}}
{{/each}}
{{else}}
  - None
{{/if}}

---
{{/each}}
{{/if}}

{{/each}}
@@TEMPLATE_END

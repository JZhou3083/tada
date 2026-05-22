---
document: "Data Source Documentation"
version: "v1.0.0"
required_sections: [Overview, Source Catalogue, Tables]
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

- This file contains developer guidance followed by the template used to generate Tableau documentation.
- The LLM should only populate values inside the TEMPLATE block and must not alter structure, headings, ordering, or delimiters.
Rules for generation
- Never add fields that do not appear in the source JSON. If a value is missing, the conditional blocks will naturally omit it.
- Never modify, reorder, or remove Handlebars control structures such as #if, #each, or comments.
- Do not include these developer notes in the final output.
Data Model Expectations
- datasources is an array of data source objects. Each should contain details for connections, tables, filters, and relationships.
- Connection metadata may vary by platform (BigQuery, SQL Server, cloud sources). Some fields may be absent and must not be fabricated.
- Table objects may represent logical tables, physical tables, or custom SQL elements. Any SQL snippet provided should remain exactly as supplied.
- Relationship objects may represent logical relationships or physical joins. Cardinality or join details may be missing based on the Tableau model type.
- Extract metadata may not appear unless the data source uses an extract. Filters and options should be listed only when they exist.
Optional counts
- Any array such as filters, tables, relationships, extract filters, or attributes may be empty.
- The surrounding conditional blocks already ensure correct omission. Do not insert placeholders like “None” unless the template explicitly instructs it.
- Counts should reflect the provided JSON data exactly.
Output Requirements
- Do not include developer notes in the final output when the template is executed.
- Output must be valid Markdown since the document is intended for human-readable technical documentation.
- Avoid adding interpretation or commentary. The output should be purely factual and based on supplied values.
@@DEVELOPER_NOTES_END

@@TEMPLATE_START

# Data Sources Documentation
<!-- ai:section=tableau_data_sources_documentation_template, expect="text" -->

### Covers connections, tables, relationships, filters, and extract settings
<!-- ai:section=covers_connections_tables_relationships_filters_and_extract_settings, expect="text" -->

## 1. Workbook Data Source Summary
<!-- ai:section=1_workbook_data_source_summary, expect="text" -->
{{datasources_summary}}

#### Datasources
| Data Source | Type | Extract | Tables |
|-------------|------|---------|--------|
{{#each datasources}}
| {{name}} | {{named_connection.connection.class}} | {{#if extract}}Yes{{else}}No{{/if}} | {{tables.length}} |
{{/each}}

#### Relationships
{{#if relationships.length}}
| Left Table | Right Table | Key |
|------------|-------------|-----|
{{#each relationships}}
| {{left_table}} | {{right_table}} | {{#each clauses}}{{key}}{{#unless @last}}, {{/unless}}{{/each}} |
{{/each}}
{{/if}}

---

## 2. Data Source Details
<!-- ai:section=2_data_source_details, expect="text" -->

{{#each datasources}}

### Data Source: {{name}}
<!-- ai:section=data_source_name, expect="text" -->

**Source type:** {{connection.type}}
**Live or Extract:** {{refresh_mode}}  {{!-- values: live | extract --}}
{{#if connection.details_present}}
**Connection details:**

- Server or Host: {{connection.server}}
- Project or Database: {{connection.database}}
- Schema or Dataset: {{connection.schema}}
- Authentication: {{connection.auth_method}}
{{#if connection.attributes.length}}
- Other attributes:
  {{#each connection.attributes}}
  - {{@key}}: {{this}}
  {{/each}}
{{/if}}
{{/if}}

{{#if extract}}
**Extract options:**

- Storage: {{extract.storage}}  {{!-- e.g., .hyper --}}
- File path or name: {{extract.file}}
- Incremental refresh field: {{extract.incremental_field}}
- Aggregate for visible dimensions: {{extract.aggregate_for_visible_dims}}  {{!-- true | false --}}
- Date rollup granularity: {{extract.rollup_date_granularity}}  {{!-- e.g., day | month | year --}}
- Extract filters count: {{extract.filters.length}}
{{#if extract.filters.length}}
- Extract filters:
  {{#each extract.filters}}
  - Field: {{field}} | Operator: {{operator}} | Values: {{values}}
  {{/each}}
{{/if}}
{{/if}}

**Data source filters count:** {{datasource_filters.length}}
{{#if datasource_filters.length}}
**Data source filters:**
{{#each datasource_filters}}

- Field: {{field}} | Operator: {{operator}} | Values: {{values}}
{{/each}}
{{/if}}

**Number of tables:** {{tables.length}}

{{#if tables.length}}

#### Tables
<!-- ai:section=tables, expect="text" -->
{{#each tables}}

##### Table: {{display_name}}
<!-- ai:section=table_display_name, expect="text" -->
- Type: {{type}}  {{!-- values: physical | logical | custom_sql --}}
- Physical name: {{physical_name}}
- Qualified identifier: {{qualified_name}}  {{!-- include catalog.project.dataset.table if available --}}
- Catalog or Project: {{catalog}}
- Schema or Dataset: {{schema}}
- Contains custom SQL: {{is_custom_sql}}
{{#if is_custom_sql}}
- SQL snippet: {{sql_snippet}}
{{/if}}
{{/each}}
{{/if}}

{{#if relationships.length}}

#### Relationships and Joins
<!-- ai:section=relationships_and_joins, expect="text" -->
- Relationship model type: {{relationship_model_type}}  {{!-- values: logical | physical | mixed --}}

{{#each relationships}}
**Relationship {{inc @index}}**

- Level: {{level}}  {{!-- logical | physical --}}
- Left table: {{left_table}}
- Right table: {{right_table}}
- Join type: {{join_type}}  {{!-- Inner | Left | Right | Full (physical joins only) --}}
- Operator: {{operator}}  {{!-- e.g., =, <>, >= for joins or NOCARDINALITY for logical relationships --}}
- Clauses:
{{#if clauses.length}}
  {{#each clauses}}
  - {{left_key}} {{operator}} {{right_key}}
  {{/each}}
{{else}}
  - None specified
{{/if}}
- Cardinality: {{cardinality}}  {{!-- one-to-one | one-to-many | many-to-one | many-to-many (logical only) --}}
- Null match behavior: {{null_match_behavior}}  {{!-- logical only, if present --}}
{{/each}}
{{/if}}

{{#if preaggregation.present}}
**Pre-aggregation**

- Is the data pre-aggregated: {{preaggregation.is_preaggregated}}
- Method: {{preaggregation.method}}  {{!-- e.g., Extract aggregate for visible dimensions, custom summary table, etc. --}}
- Notes: {{preaggregation.notes}}
{{/if}}

---

{{/each}}
@@TEMPLATE_END

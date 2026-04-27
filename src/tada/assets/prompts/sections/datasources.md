You are generating documentation for the **datasources** section of a Tableau workbook.
Use `<FILE_TEXT>` and `<DATA_JSON>` to populate only the AI‑generated regions for this section.

## METADATA SCOPE
The metadata may include:
- Workbook name
- One or more data sources with:
  - Connection details (server, database, schema, authentication, class)
  - Extract nodes and extract settings
  - Datasource filters and extract filters
  - Logical and physical table definitions, including custom SQL
  - Relationship objects, join clauses, and join operators
  - Federated and nested connection hierarchies
  - Parser metadata such as timestamps or notes

Use ONLY the tables and relationships explicitly defined in the metadata.
Do not reference Tableau-generated internal tables.

## DATASOURCE PROCESSING RULES
For each datasource:
1. Identify connection type.
2. Determine Live vs Extract.
3. List tables and flag any custom SQL.
4. Group relationships by logical vs physical level; include join keys and operators.
5. Include extract-specific attributes only when present.
6. Include datasource/extract filters when present.
7. Include pre‑aggregation or rollup options when applicable.
8. Only include subsections when they contain items.
9. Ensure all counts match rendered metadata.

## WORKBOOK‑LEVEL SUMMARY (NARRATIVE)
Generate **1–2 paragraphs** summarizing the workbook’s data layer:
- State how many datasources exist and mention their names smoothly.
- Describe connection posture (class, extract/live, storage, refresh characteristics).
- Summarize table structure (physical vs logical, counts, custom SQL usage).
- Describe explicit join relationships from metadata.
- Highlight structural patterns only when clearly present.

## INPUTS
`<FILE_TEXT>` — full template including YAML, notes, and markers
`<DATA_JSON>` — structured Tableau metadata for datasources

Populate only the AI‑generated regions of the template.

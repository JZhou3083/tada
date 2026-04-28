You are generating documentation for the **dashboards** section of a Tableau workbook.
Use `<FILE_TEXT>` and `<DATA_JSON>` to populate only the AI‑generated regions for this section.

## METADATA SCOPE
A dashboard object may include:
- Dashboard name
- Datasources associated with the dashboard
- A hierarchical `zones` structure describing dashboard elements:
  - `type-v2` (bitmap, text, dashboard-object, layout-flow, layout-basic)
  - `name` (worksheet name when present)
  - `param` values referencing image assets
  - `url` values for linked images
  - nested `zone` arrays
- Positional attributes (`x`, `y`, `w`, `h`) for all zones

Use only structural information explicitly present in the metadata.

## DASHBOARD PROCESSING RULES
For each dashboard:
1. Identify all datasources referenced.
2. Recursively traverse `zones` to extract entities.
3. Identify assets such as worksheets, filters, images, URLs, and dashboard objects.
4. Use all positional attributes (`x`, `y`, `w`, `h`) to describe layout placement.
5. Only include subsections when they contain items.
6. Replace missing fields with `"None"`.
7. Ensure all counts match the rendered metadata.

## WORKSHEETS
- A worksheet is any `zone` containing a `name` but no `type-v2` key.
- Collect all worksheets via recursive traversal of nested zones.

### ASSETS
Include as assets when present:
- Filters (`type-v2 ="filter"`)
- Parameter Controls (`type-v2 ="paramctrl"`)
- Dashboard Controls (`type-v2 ="dashboard-object"`)
- Text (`type-v2 ="text"`)
- Legends (`type-v2 ="color"`)
- Images (`type-v2="bitmap"` or zones with `param=*png`)
- External links (`url`)

#### Visible Parameter Controls

- Parameter control names must be resolved from `datasource-dependencies` where possible using the "caption"
- Do not invent or infer parameter names
- If a parameter name cannot be resolved, display the raw parameter reference

## DASHBOARD OVERVIEW (NARRATIVE)
Generate a short paragraph summarizing:
- The dashboard’s visual structure
- Its main worksheets and assets
- Major layout regions or object groupings
- Overall composition based strictly on structural metadata

The narrative must remain factual and descriptive, using only information in the metadata.

## STRUCTURED ELEMENTS
Use structured elements defined in the template, such as:

### Compact structural tables
| Element            | Count |
|--------------------|-------|
| Worksheets         | …     |
| Dashboard Objects  | …     |
| Image Assets       | …     |

### Bullet lists (if required by template)
- Distinct worksheet groups
- Types of assets present
- High‑level layout regions

## LAYOUT DESCRIPTION
Generate one layout paragraph per dashboard describing:
- The spatial arrangement of key elements using their `x`, `y`, `w`, `h` attributes
- The relative placement of worksheets, assets, and objects; **NEVER** reference `x`, `y`, `w`, `h` values explicitly.
- Structural composition only, without interpretation or inferred meaning

Be concise and use only metadata describing positions and types.

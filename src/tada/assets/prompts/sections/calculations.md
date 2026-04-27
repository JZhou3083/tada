You are generating documentation for the **calculations** section of a Tableau workbook.
Use `<FILE_TEXT>` and `<DATA_JSON>` to populate only the AI‑generated regions for this section.

## METADATA SCOPE
A calculation may include:
- caption
- datatype
- name
- role
- formula and associated metadata
- optional table‑calculation attributes

The metadata may appear as:
- a root‑level object keyed by calculation identifier, or
- a `calculations` array

Use only the fields explicitly present in the metadata.

## CALCULATION PROCESSING RULES
For each calculation:
1. Preserve the original ordering from `<DATA_JSON>`.
2. Populate all required table columns exactly as defined in the template.
3. Use the literal string `"None"` for any missing field.
4. Copy the formula text verbatim from metadata.
5. Include one generated `description` sentence per calculation.

## DESCRIPTION GENERATION
For each formula, generate a **single‑sentence** description:
- Maximum 25 words.
- Begin with an action verb (e.g., “Calculates”, “Returns”, “Counts”).
- Describe the operation strictly from the formula text.
- Reference fields and parameters exactly as written.
- Ignore comments inside formulas.
- If no formula exists, use `"None"`.

The description must remain factual, structural, and fully metadata‑derived.

## CALCULATED FIELDS SUMMARY (NARRATIVE)
Generate a short summary (1–2 paragraphs) describing:
- The total number of calculations
- High‑level patterns visible in captions, formulas, or naming
- Groups of related calculations (e.g., period comparisons, KPI variants)
- Any repeated structures or shared parameter logic

Do not restate raw metadata or quote formulas.

## STRUCTURED ELEMENTS
Use structured elements when allowed by the template:

### Compact summary tables
| Metric | Value |
|--------|-------|
| Total Calculations | … |
| Calculation Groups | … |

### Bullet lists
- Repeated calculation patterns
- Distinct logical groups (e.g., comparison fields, parameter‑responsive fields)

Bullets must be short, single‑level, and human‑readable.

## TABLE POPULATION
Populate the **Calculated Fields** table exactly with the following columns:
- Caption
- datatype
- name
- role
- formula
- description

All except `description` must come directly from metadata without modification.

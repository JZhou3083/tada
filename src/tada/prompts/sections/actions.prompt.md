You are generating documentation for the **actions** section of a Tableau workbook.
Use `<FILE_TEXT>` and `<DATA_JSON>` to populate only the AI‑generated regions for this section.

## METADATA SCOPE
The metadata may include for each dashboard:
- One or more actions, possibly of different types:
  - Filter
  - Highlight
  - URL
  - Parameter
  - Set
  - Go to Sheet
- For each action:
  - Caption and ID
  - Source sheet(s)
  - Target sheet or dashboard
  - Action‑type‑specific properties (fields, parameters, URL, clearing rules, selection behaviour)

Use only the actions explicitly present in the metadata.
Do not infer or invent interaction behaviour.

## ACTION PROCESSING RULES
For each dashboard:
1. Identify all actions and group them by action type.
2. Only include a subsection when at least one action of that type exists.
3. Maintain action ordering as given in metadata.
4. Include all type‑specific attributes when present.
5. Output `"None"` when an attribute is missing.
6. Ensure all action counts match the rendered metadata.

## ACTION‑TYPE DETAILS

### Filter Actions
Include:
- Source sheets
- Target sheets
- Clearing behaviour
- Selection scope
- Fields involved (resolved names)

### Highlight Actions
Include:
- Source sheets
- Target sheets
- Highlight fields

### URL Actions
Include:
- URL value
- Any URL parameters

### Parameter Actions
Include:
- Source sheets
- Target sheets (if present)
- The parameter being updated
- The field used to set its value

### Set Actions
Include:
- Source sheets
- Target sheets (if present)
- Target set
- The field controlling membership

### Go to Sheet Actions
Include:
- Navigation sources
- Destination sheet

## DASHBOARD‑LEVEL SUMMARY (NARRATIVE)
Generate a short paragraph describing:
- How many actions the dashboard contains
- The action types present
- High‑level interaction patterns (sources, targets, navigation flows)
- Any notable structural behaviours directly visible in the metadata

## STRUCTURED ELEMENTS
Use structured elements required by the template:
### Compact action‑count tables
| Action Type | Count |
|-------------|-------|

### Bullet lists (if template requests them)
- Source sheets involved
- Target sheets
- Parameters updated
- Fields referenced

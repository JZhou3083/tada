You are generating documentation for the **worksheets** section of a Tableau workbook.
Use `<FILE_TEXT>` and `<DATA_JSON>` to populate only the AI‑generated regions for this section.

## METADATA SCOPE
Worksheet metadata may include:
- Worksheet name
- Rows and columns shelves
- Mark type and mark‑level encodings
- Panes and mark objects
- Axes, text, color, size, shape, and detail encodings
- Associated datasource names
Only use information explicitly present in the metadata.

## WORKSHEET PROCESSING RULES

ALWAYS resolve all field references using the Aggregation-Aware Field Resolution feature in the system instructions.
For each worksheet extract the following information:

### WORKSHEET OVERVIEW (NARRATIVE)
Write a clear, plain English business summary of this Tableau worksheet.

Explain:
- What the worksheet is analysing and why it is useful from a business perspective.
- The primary metric or metrics being calculated, described conceptually rather than with formulas.
- Any key user controls such as parameters, filters, or selections, and how they affect the data shown.
- The time frame or scope of data included, including how periods are defined if relevant.
- Any important exclusions or data quality rules, such as removing refunded, cancelled, or invalid records.
- How the data is visualised and what the viewer should look for, such as trends, comparisons, highlights, or outliers.

Keep the language non technical and accessible to a business audience. Avoid field names, calculations, or Tableau specific terminology unless absolutely necessary. Focus on what insight the worksheet provides and how it supports decision making.

#### Examples of ideal output
*This worksheet shows how a key business metric changes over time within a user selected period. It allows viewers to adjust the time window to focus on recent activity or a broader timeframe. Only relevant records are included based on the applied rules, ensuring the results reflect true performance. The visual highlights patterns and fluctuations, making it easier to spot trends, spikes, or periods of decline that may require further investigation.*

*This worksheet compares performance across categories or time periods to help identify what is performing best and where improvement may be needed. Users can filter the view to focus on specific segments or adjust the scope of the data being analysed. The results are presented visually to support quick comparison, with standout values clearly identifiable. This view is designed to support prioritisation and benchmarking decisions.*

*This worksheet provides a high level overview of a core business metric within a selected timeframe. It focuses on clarity and ease of interpretation, allowing senior stakeholders to quickly assess current performance. Interactive controls enable users to adjust the scope without changing the underlying logic. The view supports fast, confident decision making by highlighting what matters most at a glance.*

### DATASOURCES
- Extract datasource names from `table.view.datasources.datasource`
- If empty, output "None".

### FILTERS
- Extract filters from `table.view.filter`
- Filter-specific enforcement (CRITICAL):
  Treat these JSON locations as field-reference contexts even if they are strings:
  - filter[*].column
  - filter[*].groupfilter.level
  - filter[*].groupfilter.groupfilter[*].level
  - filter[*].groupfilter.groupfilter[*].member
  - filter[*].groupfilter.member
- If missing or empty, output "None".


### COLUMNS SHELF
- Read the raw shelf expression from table.cols["#text"].
- Resolve ALL field references inside the expression using datasource-dependencies:
  1) Build base_field_map from datasource-dependencies.column[]
  2) Build instance_expression_map from datasource-dependencies.column-instance[]
     - Convert derivation to aggregation wrappers (Sum -> SUM(...), None -> no wrapper)
     - Apply table-calc wrappers when present (PctTotal -> PERCENT_OF_TOTAL(...))
- Replace any occurrence of:
  - a column-instance token like [sum:Calculation_...:qk]
  - or a qualified token like [federated.xxx].[sum:Calculation_...:qk]
  with its instance_expression_map value.
- Output the final resolved expression.
- If table.cols is missing, output "None".

#### ROWS SHELF
- Same process as columns but using table.rows["#text"].

### MARKS AND ENCODINGS
- Marks live under table.panes.pane (single object or array).
- For each pane:
  - Mark type is mark.class.
  - For each encoding (color, shape, size, detail, label):
    - Resolve the encoding column reference using the same instance_expression_map logic.
  - For text encodings, handle array form.
  - Resolve x-axis-name and y-axis-name using the same logic.
  - Resolve customized-tooltip runs by replacing any <[...]> tokens using the same logic.
Use only encodings present in the metadata.

### ANALYTICS PANE OBJECTS
- Located within:`table.panes.pane`
- Analytics Pane tools include:
  - Reference lines
  - Reference bands
  - Distribution bands
  - Box plots
  - Trend lines
  - Forecasts
  - Clusters

### Tooltips

- Located within:`table.panes.pane.encodings.tooltip` or `table.panes.pane.customized-tooltip`
Classify tooltip type as one of:
  - "custom" when a customized-tooltip node or equivalent exists
  - "automatic" when tooltip encodings exist without a customized-tooltip
  - "none" only neither of these conditions are true
- Detect viz-in-tooltip if the tooltip references another worksheet or a tooltip-viz node. Capture target worksheet name and any parameter or filter mappings if present.
- Extract expected layout of the tooltip as a sequence of lines and tokens in order of appearance.
  - Normalization rules
    - Treat the single character "Æ" as a hard line break. Split the tooltip into lines at every standalone "Æ" token. Denote new lines with <br>.
    - Do not trim surrounding spaces inside text runs unless they are leading or trailing whitespace.
    - Preserve field placeholders exactly as friendly field tokens without angle-bracket HTML escaping, for example "<DAY(Event Date)>".
    - Preserve the original line order defined by formatted-text runs after splitting on "Æ".
    - Decode HTML entities such as "&lt;" and "&gt;" to "<" and ">" before tokenization.
  - For custom tooltips: parse formatted-text runs. Translate field tokens to friendly names.
  - Treat consecutive instances of text as being inline.
  - For automatic tooltips: list fields in a best effort order based on shelves and mark encodings.

## STYLE & CONTENT RULES
- Narrative must be natural and human‑readable.
- Do not mirror JSON structure or restate metadata keys.
- Do not quote field names unless they represent recognizable concepts.
- Do not include numeric values, tooltips, or datasource‑level logic.
- Avoid repetitive sentence structures across worksheets.
- ALWAYS resolve all field references using the Aggregation-Aware Field Resolution feature in the system instructions.

## OUTPUT REQUIREMENT
Produce:
- **Only** the template content with populated values
- **No explanations**, **no system messages**, **no JSON**

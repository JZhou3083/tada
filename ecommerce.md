> **AI-generated documentation notice**
>
> This documentation was generated with the assistance of an AI system using Tableau workbook metadata.
> It reflects the structure and logic present in the source file at the time of generation and does not validate business intent, analytical correctness, or data quality.
> Dashboard owners remain responsible for review and approval.

# Workbook Summary: E-commerce Dataset Analysis

### Section 1 — Workbook Overview
This workbook provides a comprehensive analysis of e-commerce performance, focusing on customer behavior, product trends, and financial metrics. It is designed to support a user journey that begins with high-level executive KPIs and transitions into granular product-level exploration. The workbook is structured around two primary dashboards supported by a unified data model, utilizing 14 filter actions and 6 parameter actions to drive interactivity.

**Workbook Scale:**
*   **Dashboards:** 2
*   **Data Sources:** 1 (Federated Extract)
*   **Parameters:** 5
*   **Total Actions:** 20

### Section 2 — Dashboards & Analytical Flow
The analytical experience is divided into two distinct stages: broad performance monitoring and specific product deep-dives. The **Dashboard** serves as the primary entry point, focusing on core business health through metrics like Revenue, Quantity, and Average Order Value (AOV). Users can explore trends such as Gross vs. Net performance and Revenue vs. Customers. The **Product** dashboard provides a more specialized view, allowing users to analyze performance across demographics (Age Band, Country) and purchasing behavior (Channel, Segment, Payment Method). Navigation is seamless, as selecting marks on summary worksheets automatically filters the broader dashboard view to isolate specific segments or timeframes.

### Section 3 — Datasources & Data Model
The workbook relies on a single federated data source containing three logical tables. The data is stored as a Hyper extract derived from an Excel connection, ensuring optimized performance for interactive filtering.

**Data Source Summary**
| Data Source | Type | Extract | Tables |
| :--- | :--- | :--- | :--- |
| Customers (DataDNA Dataset Challenge) | Federated | Yes | 3 |

**Key Relationships**
| Left Table | Right Table | Key |
| :--- | :--- | :--- |
| Events | Customers | [customer_id] = [customer_id (Customers)] |
| Events | Products | [product_id] = [product_id (Products)] |

The model uses a star-schema-like logical structure where the **Events** table acts as the central fact table, linked to **Customers** and **Products** dimensions via their respective identifiers.

### Section 4 — Interaction Behaviour (Actions & Parameters)
Interactivity is driven by a combination of global filter actions and targeted parameter updates. The workbook employs a "select-to-filter" pattern where clicking on a chart element updates all other visualizations on the dashboard.

**Workbook Interaction Statistics**
| Action Type | Count | Primary Behavior |
| :--- | :--- | :--- |
| Filter Actions | 14 | On-select activation with auto-clear on deselect. |
| Parameter Actions | 6 | Updates metrics, product selection, and UI visibility. |

Key interaction patterns include:
*   **Dynamic Metric Switching:** Users can toggle the entire view between Revenue, Quantity, and Customer counts using the Metric Selector.
*   **Product Selection:** A dedicated parameter action allows users to update the "Product Name Parameter" by selecting items from a list, which then propagates through the Product dashboard.
*   **UI Control:** Parameters are used to toggle the visibility of specific elements (Show/Hide) to manage dashboard real estate.

### Section 5 — Complexity & Maintenance Notes
The workbook demonstrates a highly standardized design pattern, particularly in its use of generated filter actions that target all fields. Maintenance is simplified by the use of a single extract and a logical relationship model, which avoids the complexity of physical joins. 

**Key Observations:**
*   **Parameter Dependency:** The workbook relies heavily on five parameters to control date ranges (Last 7 to 90 days), metric types, and product-specific filtering.
*   **Consistent Action Logic:** All 14 filter actions are configured to "auto-clear," ensuring the dashboard returns to a default state when selections are removed.
*   **Standardized Dimensions:** Analysis is consistently broken down by a fixed set of dimensions including Category, Segment, and Country across both dashboards.

# Data Sources Documentation

### Covers connections, tables, relationships, filters, and extract settings

## 1. Workbook Data Source Summary
The workbook contains a single federated data source named Customers (DataDNA Dataset Challenge - E-commerce Dataset - November 2025). This data source is configured as an extract using the Hyper storage engine, derived from an Excel connection.

The data model consists of three logical tables: Events, Customers, and Products. These tables are connected via logical relationships rather than physical joins, using customer and product identifiers to link the event data to its respective dimensions.

#### Datasources
| Data Source | Type | Extract | Tables |
|-------------|------|---------|--------|
| Customers (DataDNA Dataset Challenge - E-commerce Dataset - November 2025) | federated | Yes | 3 |

#### Relationships
| Left Table | Right Table | Key |
|------------|-------------|-----|
| Events | Customers | [customer_id] = [customer_id (Customers)] |
| Events | Products | [product_id] = [product_id (Products)] |

---

## 2. Data Source Details

### Data Source: Customers (DataDNA Dataset Challenge - E-commerce Dataset - November 2025)

**Source type:** federated
**Live or Extract:** extract  

**Extract options:**

- Storage: hyper
- File path or name: Data/TableauTemp/TEMP_0xfnzak033ztnc13wohgv0xghqq0.hyper
- Incremental refresh field: None
- Aggregate for visible dimensions: false
- Date rollup granularity: None
- Extract filters count: 0

**Data source filters count:** 0

**Number of tables:** 3

#### Tables

##### Table: Events
- Type: logical
- Physical name: Events
- Qualified identifier: [Events$]
- Catalog or Project: None
- Schema or Dataset: None
- Contains custom SQL: false

##### Table: Customers
- Type: logical
- Physical name: Customers
- Qualified identifier: [Customers$]
- Catalog or Project: None
- Schema or Dataset: None
- Contains custom SQL: false

##### Table: Products
- Type: logical
- Physical name: Products
- Qualified identifier: [Products$]
- Catalog or Project: None
- Schema or Dataset: None
- Contains custom SQL: false

#### Relationships and Joins
- Relationship model type: logical

**Relationship 1**

- Level: logical
- Left table: Events
- Right table: Customers
- Join type: None
- Operator: =
- Clauses:
  - [customer_id] = [customer_id (Customers)]
- Cardinality: None
- Null match behavior: None

**Relationship 2**

- Level: logical
- Left table: Events
- Right table: Products
- Join type: None
- Operator: =
- Clauses:
  - [product_id] = [product_id (Products)]
- Cardinality: None
- Null match behavior: None

---

# Actions Documentation

## 1. Workbook Overview
**Workbook Name:** None

---

## 2. Dashboard Interaction Summary

### Dashboard: Dashboard

**Summary:**
The Dashboard contains 6 filter actions that facilitate interactive data exploration. These actions are triggered by selecting marks on various worksheets, including Revenue, Quantity, AOV, Avg. Days to 2nd Purchase, Gross vs. Net, and Revenue vs. Customers. Each action is configured to filter all relevant fields across the dashboard and automatically clears the filter when the selection is removed.

**Action Counts:**
| Action Type | Count |
|-------------|-------|
| filter | 6 |

---

## Filter Actions

### Filter Action: Filter 9 (generated)
- **Purpose:** None
- **Source Worksheet:** Revenue
- **Target Dashboard:** Dashboard
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Dashboard

---

### Filter Action: Filter 10 (generated)
- **Purpose:** None
- **Source Worksheet:** Quantity
- **Target Dashboard:** Dashboard
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Dashboard

---

### Filter Action: Filter 11 (generated)
- **Purpose:** None
- **Source Worksheet:** AOV
- **Target Dashboard:** Dashboard
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Dashboard

---

### Filter Action: Filter 12 (generated)
- **Purpose:** None
- **Source Worksheet:** Avg. Days to 2nd Purchase
- **Target Dashboard:** Dashboard
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Dashboard

---

### Filter Action: Filter 13 (generated)
- **Purpose:** None
- **Source Worksheet:** Gross vs. Net
- **Target Dashboard:** Dashboard
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Dashboard

---

### Filter Action: Filter 14 (generated)
- **Purpose:** None
- **Source Worksheet:** Revenue vs. Customers
- **Target Dashboard:** Dashboard
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Dashboard

---

### Dashboard: Product

**Summary:**
The Product dashboard features a complex interaction model consisting of 8 filter actions and 6 parameter actions. The filter actions allow users to drill down into data via worksheets such as Age Band, Country, Channel, and Segment. The parameter actions enable dynamic updates to workbook parameters, including Product Name Parameter and various metric selectors, allowing for a highly customizable view of product performance and metrics.

**Action Counts:**
| Action Type | Count |
|-------------|-------|
| filter | 8 |
| parameter | 6 |

---

## Filter Actions

### Filter Action: Filter 4 (generated)
- **Purpose:** None
- **Source Worksheet:** Age Band
- **Target Dashboard:** Product
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Product

---

### Filter Action: Filter 5 (generated)
- **Purpose:** None
- **Source Worksheet:** Country
- **Target Dashboard:** Product
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Product

---

### Filter Action: Filter 6 (generated)
- **Purpose:** None
- **Source Worksheet:** Channel
- **Target Dashboard:** Product
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Product

---

### Filter Action: Filter 7 (generated)
- **Purpose:** None
- **Source Worksheet:** Segment
- **Target Dashboard:** Product
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Product

---

### Filter Action: Filter 8 (generated)
- **Purpose:** None
- **Source Worksheet:** Payment Method
- **Target Dashboard:** Product
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Product

---

### Filter Action: Filter 1 (generated)
- **Purpose:** None
- **Source Worksheet:** Prod. Qty
- **Target Dashboard:** Product
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Product

---

### Filter Action: Filter 2 (generated)
- **Purpose:** None
- **Source Worksheet:** Prod. Revenue
- **Target Dashboard:** Product
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Product

---

### Filter Action: Filter 3 (generated)
- **Purpose:** None
- **Source Worksheet:** CLV
- **Target Dashboard:** Product
- **Activation Type:** on-select
- **Auto Clear:** true
- **Filter Parameters:**
  - special-fields: all
  - target: Product

---

## Parameter Actions

### Parameter Action: Product
- **Purpose:** None
- **Source Worksheet:** Select Products
- **Parameter Updated:** [Parameters].[Product Name Parameter]
- **Source Field:** [product_name]
- **Activation Type:** on-select
- **Clear Option:** do-nothing

---

### Parameter Action: Show
- **Purpose:** None
- **Source Worksheet:** Show
- **Parameter Updated:** [Parameters].[Parameter 3]
- **Source Field:** [Calculation_1724882428862467]
- **Activation Type:** on-select
- **Clear Option:** do-nothing

---

### Parameter Action: Hide
- **Purpose:** None
- **Source Worksheet:** Hide
- **Parameter Updated:** [Parameters].[Parameter 3]
- **Source Field:** [Calculation_1724882430001156]
- **Activation Type:** on-select
- **Clear Option:** do-nothing

---

### Parameter Action: Revenue
- **Purpose:** None
- **Source Worksheet:** Metric Selector
- **Parameter Updated:** [Parameters].[Parameter 2]
- **Source Field:** [2 (copy)_1362057428003794984]
- **Activation Type:** on-select
- **Clear Option:** do-nothing

---

### Parameter Action: Quantity
- **Purpose:** None
- **Source Worksheet:** Metric Selector
- **Parameter Updated:** [Parameters].[Parameter 2]
- **Source Field:** [3 (copy)_1362057428003680295]
- **Activation Type:** on-select
- **Clear Option:** do-nothing

---

### Parameter Action: Customers
- **Purpose:** None
- **Source Worksheet:** Metric Selector
- **Parameter Updated:** [Parameters].[Parameter 2]
- **Source Field:** [Calculation_1362057428003586086]
- **Activation Type:** on-select
- **Clear Option:** do-nothing

---

# Tableau Parameters Documentation Template

The workbook contains 5 parameters used to control data filtering, metric selection, and display options. These parameters include 3 string-based selectors and 2 integer-based selectors, all of which utilize a list of allowable values to provide specific user options.

**Parameter Counts:**
- string: 3
- integer: 2

---

## Parameters

The following parameters are defined at the workbook level.

### Parameter Category Parameter
- **Purpose:** None
- **Datatype** string
- **Name** [Category Parameter]
- **Param Domain Type** list
- **Role** measure
- **Type** nominal
- **Default Value** "AI Productivity"
- **Members**
- value: "Add-on"
- value: "AI Productivity"
- value: "AI Tools"
- value: "Analytics"
- value: "Collaboration"
- value: "Design"
- value: "Developer Tools"
- value: "File Storage"
- value: "Infrastructure"
- value: "Monitoring"
- value: "Perpetual"
- value: "Productivity"
- value: "Productivity Suite"
- value: "Project Management"
- value: "Security"
- value: "Services"
- value: "Support"

---

### Parameter Select Date
- **Purpose:** None
- **Datatype** integer
- **Name** [Parameter 1]
- **Param Domain Type** list
- **Role** measure
- **Type** quantitative
- **Default Value** 21
- **Members**
- value: 7 - alias:Last 7 Days 
- value: 14 - alias:Last 14 Days 
- value: 21 - alias:Last 21 Days 
- value: 30 - alias:Last 30 Days 
- value: 90 - alias:Last 90 Days 
- value: 547 - alias:Year to Date 

---

### Parameter Metric
- **Purpose:** None
- **Datatype** integer
- **Name** [Parameter 2]
- **Param Domain Type** list
- **Role** measure
- **Type** quantitative
- **Default Value** 1
- **Members**
- value: 1 - alias:Revenue 
- value: 2 - alias:Quantity 
- value: 3 - alias:Customers 

---

### Parameter Show/hide
- **Purpose:** None
- **Datatype** string
- **Name** [Parameter 3]
- **Param Domain Type** list
- **Role** measure
- **Type** nominal
- **Default Value** "Show"
- **Members**
- value: "Show"
- value: "Hide"

---

### Parameter Product Name Parameter
- **Purpose:** None
- **Datatype** string
- **Name** [Product Name Parameter]
- **Param Domain Type** list
- **Role** measure
- **Type** nominal
- **Default Value** "Microsoft Copilot for Office Annual"
- **Members**
- value: "Adobe Creative Cloud All Apps Annual"
- value: "Adobe Creative Cloud All Apps Monthly"
- value: "Adobe Firefly Creative AI Annual"
- value: "Adobe Firefly Creative AI Annual Business"
- value: "Adobe Firefly Creative AI Annual Pro"
- value: "Adobe Firefly Creative AI Annual Standard"
- value: "Adobe Firefly Creative AI Monthly"
- value: "Adobe Firefly Creative AI Monthly Business"
- value: "Adobe Firefly Creative AI Monthly Pro"
- value: "Adobe Firefly Creative AI Monthly Standard"
- value: "Advanced Reports Add‑on Annual"
- value: "Advanced Reports Add‑on Monthly"
- value: "AI Analytics Add‑on Annual"
- value: "AI Analytics Add‑on Monthly"
- value: "AI Assistant Add‑on Annual"
- value: "AI Assistant Add‑on Monthly"
- value: "Airtable Team Annual"
- value: "Airtable Team Monthly"
- value: "Asana Premium Annual"
- value: "Asana Premium Monthly"
- value: "Azure AI Studio Annual"
- value: "Azure AI Studio Annual Pro"
- value: "Azure AI Studio Annual Standard"
- value: "Azure AI Studio Monthly"
- value: "Azure AI Studio Monthly Pro"
- value: "Azure AI Studio Monthly Standard"
- value: "Canva Pro Annual"
- value: "Canva Pro Monthly"
- value: "ChatGPT Team Annual"
- value: "ChatGPT Team Annual Business"
- value: "ChatGPT Team Annual Pro"
- value: "ChatGPT Team Annual Standard"
- value: "ChatGPT Team Monthly"
- value: "ChatGPT Team Monthly Pro"
- value: "ChatGPT Team Monthly Standard"
- value: "Cloud Storage 1TB Annual"
- value: "Cloud Storage 1TB Monthly"
- value: "Datadog Pro Annual"
- value: "Datadog Pro Monthly"
- value: "Dropbox Standard Annual"
- value: "Dropbox Standard Monthly"
- value: "Endpoint Security Annual"
- value: "Endpoint Security Monthly"
- value: "Figma Professional Annual"
- value: "Figma Professional Monthly"
- value: "Freshdesk Growth Annual"
- value: "Freshdesk Growth Monthly"
- value: "GitHub Copilot Business Annual"
- value: "GitHub Copilot Business Monthly"
- value: "JetBrains All Products Pack Annual"
- value: "JetBrains All Products Pack Monthly"
- value: "Jira Software Standard Annual"
- value: "Jira Software Standard Monthly"
- value: "Microsoft 365 Business Standard Annual"
- value: "Microsoft 365 Business Standard Monthly"
- value: "Microsoft Copilot for Office Annual"
- value: "Microsoft Copilot for Office Annual Business"
- value: "Microsoft Copilot for Office Annual Pro"
- value: "Microsoft Copilot for Office Annual Standard"
- value: "Microsoft Copilot for Office Monthly"
- value: "Microsoft Copilot for Office Monthly Business"
- value: "Microsoft Copilot for Office Monthly Pro"
- value: "Microsoft Copilot for Office Monthly Standard"
- value: "Miro Business Annual"
- value: "Miro Business Monthly"
- value: "Monday.com Standard Annual"
- value: "Monday.com Standard Monthly"
- value: "Notion AI Annual"
- value: "Notion AI Annual Standard"
- value: "Notion AI Monthly"
- value: "Notion AI Monthly Business"
- value: "Notion AI Monthly Pro"
- value: "Notion AI Monthly Standard"
- value: "Notion Plus Annual"
- value: "Notion Plus Monthly"
- value: "Onboarding Training Pack One-time"
- value: "Perpetual License (Legacy) One-time"
- value: "Power BI Pro Annual"
- value: "Power BI Pro Annual Business"
- value: "Power BI Pro Annual Pro"
- value: "Power BI Pro Annual Standard"
- value: "Power BI Pro Monthly"
- value: "Power BI Pro Monthly Business"
- value: "Power BI Pro Monthly Pro"
- value: "Power BI Pro Monthly Standard"
- value: "Priority Support Annual"
- value: "Priority Support Monthly"
- value: "Slack Huddles Add‑on Annual"
- value: "Slack Huddles Add‑on Monthly"
- value: "Slack Pro Annual"
- value: "Slack Pro Monthly"
- value: "Tableau Creator Annual"
- value: "Tableau Creator Monthly"
- value: "Team Seats Add‑on Annual"
- value: "Team Seats Add‑on Monthly"
- value: "Zendesk Suite Team Annual"
- value: "Zendesk Suite Team Monthly"
- value: "Zoom Pro Annual"
- value: "Zoom Pro Monthly"
- value: "Zoom Whiteboard Add‑on Annual"
- value: "Zoom Whiteboard Add‑on Monthly"

---
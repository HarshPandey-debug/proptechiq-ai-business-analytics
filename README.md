# AI-Powered Business Analytics Assistant (Synthetic Student Housing Marketplace)

An end-to-end **Business Analytics & Text-to-SQL AI Engineering Portfolio Project** built with **PostgreSQL**, **Python (Pandas/NumPy)**, **Google Gemini 2.0 Flash (`google-genai`)**, and **Power BI (DAX)**.

> **Synthetic Dataset Disclosure**: This project uses a **100% synthetic, simulated student-housing marketplace dataset ("CampusStay PBSA Marketplace")** generated programmatically via `src/generate_dataset.py` (28 simulated PBSA properties across 6 UK university cities, 650 student profiles, 1,100 cleaned bookings, and 3,250 installment payments). It does not contain proprietary data from any real-world company.

This repository demonstrates production-grade data cleaning, SQL business analytics, AI-assisted SQL generation with join-grain guardrails, Power BI star-schema modeling, and manual verification against source data—including a full post-mortem of an actual **1-to-many SQL join fan-out mistake** made by an unguarded LLM query and how it was corrected.

## Repository Architecture

```text
ai-business-analytics-assistant-proptech/
├── README.md                                        # Project overview, reconciled KPI tables & quick-start
├── requirements.txt                                 # Python dependencies (pandas, sqlalchemy, google-genai)
├── .env.example                                     # Environment config for GEMINI_API_KEY and DATABASE_URL
├── src/
│   ├── generate_dataset.py                          # Synthetic dataset generator with intentional raw anomalies
│   ├── data_cleaning.py                             # 7-stage Pandas data cleaning, imputation & validation pipeline
│   ├── ai_analytics_assistant.py                    # Gemini 2.0 Flash Text-to-SQL & Executive Interpretation agent
│   ├── verify_ai_vs_ground_truth.py                 # Automated & manual reconciliation suite (SQL vs. Pandas vs. JSON)
│   └── render_dashboard_preview.py                  # Renders 4-panel executive dashboard preview (PNG)
├── sql/
│   ├── 01_schema_and_load.sql                       # PostgreSQL 15+ DDL schema, constraints, indexes & COPY load
│   ├── 02_business_analytics_queries.sql            # Production SQL: Revenue/Profit, Segmentation, Monthly Trends, ROAS
│   └── 03_ai_mistake_and_fix.sql                    # Side-by-side comparison of Broken AI Fan-Out SQL vs. Fixed CTE SQL
├── powerbi/
│   ├── POWER_BI_DASHBOARD_SPEC_AND_DAX.md           # Star schema model, visual wireframes & setup guide
│   ├── dax_measures.dax                             # 16 production DAX measures for Power BI Desktop
│   └── dashboard_preview.png                        # 4-panel executive dashboard visual preview
├── docs/
│   └── AI_MISTAKE_AND_VERIFICATION_REPORT.md        # Engineering post-mortem of the +478.37% AI SQL fan-out bug
└── data/
    ├── raw/                                         # Synthetic raw CSVs containing 379 intentional data anomalies
    └── cleaned/                                     # Cleaned CSVs + penny-reconciled JSON audit logs
```

## 1. Python / Pandas Data Cleaning & Validation (`src/data_cleaning.py`)

`src/data_cleaning.py` executes a 7-stage deterministic validation pipeline across the synthetic raw CSVs in `data/raw/` before any data enters PostgreSQL or Power BI:

| Validation Stage | Target Table | Raw Anomalies Fixed | Pipeline Rule Applied |
| :--- | :--- | ---: | :--- |
| **1. Webhook Deduplication** | `bookings_raw.csv` | **42 duplicate rows** | `.drop_duplicates(subset=['booking_id'], keep='first')` |
| **2. QA Test Bot Removal** | `students_raw.csv` & `bookings_raw.csv` | **10 students / 12 bookings** | Filtered out `STU-TEST-*` and `@campusstay-qa.internal` test rows |
| **3. Currency String Parsing** | `bookings_raw.csv` | **146 formatted rows** | Stripped `£` and `,` from `"£1,200.00"` and cast to `float64` |
| **4. Corrupted Value Quarantine** | `bookings_raw.csv` | **15 invalid rows** | Quarantined rows with `lease_weeks <= 0` or `weekly_rent_gbp <= 0` |
| **5. Status & City Normalization** | `bookings` & `properties` | **114 dirty strings** | Standardized `" LONDON, UK "` → `"London"` and status title-casing |
| **6. Missing Value Imputation** | `properties`, `students`, `bookings` | **105 missing values** | Imputed `partner_commission_pct` by room tier, `check_in_date` by intake, and `acquisition_channel` to `'Unattributed / Direct'` |
| **7. Schema Invariant Assertions** | All Cleaned Tables | **0 violations post-clean** | Asserted primary key uniqueness, referential integrity, and positive numeric bounds |

## 2. PostgreSQL Analytics: Revenue, Profit, Segmentation & Monthly Trends (`sql/02_business_analytics_queries.sql`)

All SQL queries in `sql/02_business_analytics_queries.sql` are 100% reconciled (`£0.00` variance) with `data/cleaned/data_quality_audit_report.json` and `data/cleaned/verification_summary.json`.

### 2.1 Revenue, Direct Cost & Net Profit by City (Confirmed Bookings)

| City | Confirmed Bookings | Avg Lease (Wks) | Gross Booking Value (£) | Platform Revenue (£) | Direct Cost (£) | Net Profit (£) | Net Profit Margin (%) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **London** | 273 | 42.6 | £4,812,140.00 | £391,944.65 | £76,655.21 | £315,289.44 | 80.44% |
| **Edinburgh** | 151 | 42.9 | £1,876,360.00 | £151,192.36 | £37,906.27 | £113,286.09 | 74.93% |
| **Manchester** | 133 | 42.3 | £1,441,720.00 | £118,762.32 | £33,187.87 | £85,574.45 | 72.06% |
| **Birmingham** | 129 | 43.1 | £1,336,136.00 | £108,567.14 | £30,416.60 | £78,150.54 | 71.98% |
| **Nottingham** | 131 | 44.5 | £1,298,828.00 | £106,277.90 | £31,171.19 | £75,106.71 | 70.67% |
| **Glasgow** | 128 | 42.8 | £1,301,380.00 | £104,874.12 | £30,355.07 | £74,519.05 | 71.06% |
| **Total / Overall** | **945** | **43.0** | **£12,066,564.00** | **£981,618.49** | **£239,692.21** | **£741,926.28** | **75.58%** |

### 2.2 Student Customer Segmentation (Cohort × Study Level & Monetary LTV Tiers)

* **Cohort × Study Level**: **International Postgraduate (Masters)** students generate **£394,324.59** in platform commission revenue (**£297,602.42** net profit across **382 bookings**), while **International Undergraduates** generate **£250,541.55** (**£189,383.82** net profit across **239 bookings**). Combined, International students account for **78.96% (£775,055.62)** of total recognized revenue.
* **Monetary LTV Tiers (Query 2B)**: Using CTEs and `SUM() OVER ()` window functions, **VIP Platinum (`>= £1,800 Rev`)** students represent **47.91% of active students (241 students)** and drive **72.52% (£711,858.06)** of total platform revenue.

### 2.3 Monthly Revenue Trends, MoM Growth & 3-Month Rolling Average (Nov 2025 – Oct 2026)

| Booking Month | Confirmed Bookings | Monthly GBV (£) | Monthly Revenue (£) | Monthly Net Profit (£) | MoM Revenue Growth (%) | 3M Rolling Avg Revenue (£) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **2025-11** | 50 | £613,388.00 | £50,192.69 | £37,447.01 | — | £50,192.69 |
| **2025-12** | 79 | £1,013,360.00 | £82,923.72 | £63,101.81 | +65.21% | £66,558.21 |
| **2026-01** | 86 | £1,153,752.00 | £93,899.42 | £72,125.64 | +13.24% | £75,671.94 |
| **2026-02** | 62 | £793,308.00 | £63,294.73 | £48,253.87 | -32.59% | £80,039.29 |
| **2026-03** | 57 | £694,016.00 | £56,279.68 | £41,704.20 | -11.08% | £71,157.94 |
| **2026-04** | 77 | £1,030,500.00 | £84,308.95 | £64,226.15 | +49.80% | £67,961.12 |
| **2026-05** | 100 | £1,246,532.00 | £101,740.36 | £75,974.92 | +20.68% | £80,776.33 |
| **2026-06** | 128 | £1,782,500.00 | £146,321.78 | £113,205.05 | +43.82% | £110,790.36 |
| **2026-07** | 129 | £1,566,688.00 | £127,096.82 | £94,738.93 | -13.14% | £125,052.99 |
| **2026-08** | 104 | £1,252,768.00 | £101,088.92 | £74,998.89 | -20.46% | £124,835.84 |
| **2026-09** | 39 | £516,264.00 | £42,091.46 | £32,063.06 | -58.36% | £90,092.40 |
| **2026-10** | 34 | £403,488.00 | £32,379.96 | £24,086.75 | -23.07% | £58,520.11 |

## 3. Gemini 2.0 Flash SQL & Interpretation Assistant (`src/ai_analytics_assistant.py`)

`src/ai_analytics_assistant.py` integrates **Google Gemini (`gemini-2.0-flash`)** with PostgreSQL to:
1. Convert natural language business questions into executable PostgreSQL queries using schema-aware prompting (`SCHEMA_CONTEXT`).
2. Enforce **Read-Only DDL/DML Safety** and **Anti-Fan-Out Static Analysis (`validate_sql_safety_and_grain`)** prior to database execution.
3. Synthesize verified query outputs into executive business commentary citing exact metrics.

## 4. Manual Verification & Documented AI Mistake (`docs/AI_MISTAKE_AND_VERIFICATION_REPORT.md`)

When asked to report **Gross Booking Value, Platform Commission Revenue, Net Profit, and Collected Installment Payments by City**, an unguarded AI prompt generated a flat `LEFT JOIN` across `bookings` (`1 row per booking`), `payment_installments` (`1–4 rows per booking`), and `property_promotions` (`1–3 rows per property`).

* **Impact of the AI Mistake**: The 1-to-many join fan-out multiplied booking-level metrics by `(num_installments × num_promotions)`, inflating reported confirmed bookings from **945 to 5,625 (+495.24%)**, overstating Platform Commission Revenue from **£981,618.49 to £5,677,352.25 (+478.37%)**, and falsely ranking **Manchester (£956,516.22 inflated)** ahead of **Edinburgh (£824,544.99 inflated)**.
* **How It Was Caught & Fixed**: Caught via manual reconciliation against Pandas ground-truth aggregations (`src/verify_ai_vs_ground_truth.py`). Fixed by pre-aggregating `payment_installments` by `booking_id` inside a CTE (`WITH booking_payments AS (...)`) prior to joining to `bookings`, and adding a static fan-out guardrail in `src/ai_analytics_assistant.py`.

## 5. Power BI Executive Dashboard (`powerbi/`)

* **Data Model**: Star Schema (`Fact_Bookings`, `Fact_Payments`, `Dim_Properties`, `Dim_Students`, `Dim_Calendar`) with single-direction cross-filtering so `Fact_Payments` never fans out `Fact_Bookings`.
* **DAX Measures**: 16 production measures in `powerbi/dax_measures.dax` (`[Confirmed Gross Booking Value (GBV)]`, `[Recognized Commission Revenue]`, `[Confirmed Net Profit]`, `[Fully Loaded Net Profit (Incl. Sunk CPA)]`, `[MoM Revenue Growth %]`, `[Rolling 3M Avg Revenue]`, `[Marketing ROAS (x)]`).

## 6. Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Regenerate synthetic raw data and run the Pandas cleaning & validation pipeline
python3 src/generate_dataset.py
python3 src/data_cleaning.py

# 3. Run the SQL vs. Pandas manual verification suite & AI mistake audit
python3 src/verify_ai_vs_ground_truth.py

# 4. Run the Gemini AI Analytics Assistant (Demo mode or custom question)
export GEMINI_API_KEY="your-api-key"
python3 src/ai_analytics_assistant.py --demo
```

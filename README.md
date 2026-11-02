# PropTechIQ

## AI-Powered Business Analytics Assistant

An end-to-end analytics and Text-to-SQL portfolio project for a synthetic
student-housing marketplace. PropTechIQ combines deterministic data quality
engineering, PostgreSQL analytics, Google Gemini, and Power BI-ready metrics.

> **Dataset:** 100% synthetic CampusStay PBSA Marketplace data. It contains no
> proprietary or real customer information.

## What this project demonstrates

- Reproducible synthetic data generation with realistic anomalies
- Seven-stage Pandas cleaning and validation pipeline
- PostgreSQL schema design and business analytics SQL
- Natural-language Text-to-SQL with Gemini `gemini-2.5-flash`
- Read-only SQL and anti-fan-out safety guardrails
- Independent SQL-versus-Pandas reconciliation
- Power BI star-schema design and DAX measures
- Executive dashboard preview generated from verified metrics

## Headline results

| KPI | Verified result |
| --- | ---: |
| Properties | 28 |
| Cleaned students | 650 |
| Cleaned bookings | 1,100 |
| Payment installments | 3,250 |
| Confirmed bookings | 945 |
| Confirmed GBV | £12,066,564.00 |
| Recognized revenue | £981,618.49 |
| Net profit | £741,926.28 |
| SQL/Pandas variance | £0.00 |

## Architecture

```text
Synthetic generator
        ↓
Raw CSV data with intentional anomalies
        ↓
Pandas cleaning, quarantine and validation
        ↓
Clean CSVs + JSON audit/verification reports
        ↓
PostgreSQL analytics (SQLite fallback for local demos)
        ↓
Gemini Text-to-SQL → safety checks → query execution
        ↓
Verified result tables, executive interpretation and dashboard preview
```

## Repository structure

```text
├── data/
│   ├── raw/                         # Generated source CSVs
│   └── cleaned/                     # Cleaned data and verification reports
├── src/
│   ├── generate_dataset.py          # Reproducible synthetic data generator
│   ├── data_cleaning.py             # Cleaning and validation pipeline
│   ├── ai_analytics_assistant.py    # Gemini Text-to-SQL assistant
│   ├── verify_ai_vs_ground_truth.py # SQL/Pandas reconciliation suite
│   └── render_dashboard_preview.py  # Matplotlib dashboard preview renderer
├── sql/
│   ├── 01_schema_and_load.sql       # PostgreSQL DDL and data loading
│   ├── 02_business_analytics_queries.sql
│   └── 03_ai_mistake_and_fix.sql    # Fan-out demonstration and correction
├── powerbi/
│   ├── POWER_BI_DASHBOARD_SPEC_AND_DAX.md
│   ├── dax_measures.dax
│   └── dashboard_preview.png
├── docs/
│   └── AI_MISTAKE_AND_VERIFICATION_REPORT.md
├── .env.example
├── requirements.txt
└── README.md
```

## Data pipeline

The deterministic cleaning pipeline in
[`src/data_cleaning.py`](src/data_cleaning.py) performs:

1. Booking deduplication by `booking_id`
2. Removal of QA/test students and bookings
3. Currency and numeric parsing
4. Quarantine of invalid lease and rent values
5. City and status normalization
6. Rule-based missing-value imputation
7. Financial derivation and schema invariant assertions

The pipeline writes cleaned CSVs, quarantined records, and an audit report to
`data/cleaned/`.

## Business metrics

The SQL layer covers:

- Confirmed GBV, recognized commission revenue, direct cost and net profit
- City and room-tier performance
- Customer segmentation by cohort and study level
- Monetary LTV tiers
- Monthly revenue, month-over-month growth and rolling averages
- Acquisition-channel performance and ROAS

Financial definitions:

```text
Gross Booking Value = lease_weeks × weekly_rent_gbp
Recognized Revenue   = GBV × (partner_commission_pct ÷ 100)
Direct Cost          = marketing_cpa_gbp + ops_servicing_cost_gbp
Net Profit           = Recognized Revenue − Direct Cost
```

Revenue is recognized only for confirmed bookings.

## AI assistant and safety design

The assistant in
[`src/ai_analytics_assistant.py`](src/ai_analytics_assistant.py) follows:

```text
Business question
      ↓
Gemini SQL generation
      ↓
Read-only and grain validation
      ↓
PostgreSQL or SQLite execution
      ↓
Verified result table
      ↓
Executive interpretation
```

Safety controls include:

- Blocks destructive SQL such as `DROP`, `DELETE`, `UPDATE` and `INSERT`
- Accepts only `SELECT` or `WITH` queries
- Detects unsafe joins from one-to-many tables
- Requires pre-aggregation CTEs before joining installment or promotion data
- Reconciles important metrics against independent Pandas calculations

### The fan-out problem

Joining booking-level facts directly to payment installments or property
promotions multiplies financial values. In this project, the unsafe query
inflated confirmed bookings from **945 to 5,625** and revenue from
**£981,618.49 to £5,677,352.25**.

The fix is to aggregate one-to-many tables first:

```sql
WITH booking_payments AS (
    SELECT booking_id, SUM(installment_amount_gbp) AS collected_payments_gbp
    FROM payment_installments
    GROUP BY booking_id
)
```

See the full post-mortem in
[`docs/AI_MISTAKE_AND_VERIFICATION_REPORT.md`](docs/AI_MISTAKE_AND_VERIFICATION_REPORT.md).

## Quick start

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src\generate_dataset.py
.\.venv\Scripts\python.exe src\data_cleaning.py
.\.venv\Scripts\python.exe src\verify_ai_vs_ground_truth.py
.\.venv\Scripts\python.exe src\render_dashboard_preview.py
```

### Configure Gemini

Copy `.env.example` to `.env` and add your key:

```powershell
Copy-Item .env.example .env
```

Then set:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=
```

Leave `DATABASE_URL` blank to use the local in-memory SQLite fallback. Set it
to a PostgreSQL connection string when using the production-style database
path.

Run the live assistant or offline demo:

```powershell
.\.venv\Scripts\python.exe src\ai_analytics_assistant.py --demo
.\.venv\Scripts\python.exe src\ai_analytics_assistant.py --question "Show confirmed revenue and net profit by city."
```

## Verification outputs

- [`data_quality_audit_report.json`](data/cleaned/data_quality_audit_report.json)
- [`verification_summary.json`](data/cleaned/verification_summary.json)
- [`dashboard_preview.png`](powerbi/dashboard_preview.png)
- [`POWER_BI_DASHBOARD_SPEC_AND_DAX.md`](powerbi/POWER_BI_DASHBOARD_SPEC_AND_DAX.md)

The dashboard preview is a locally rendered Matplotlib image based on verified
JSON metrics. The Power BI folder contains the production-oriented model and
DAX specification.

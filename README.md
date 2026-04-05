## NSW Property Sales

An end-to-end data pipeline that ingests every NSW property sale recorded since 1990 — over **150,000 files processed**, **35+ years** of transactions, updated automatically every Monday.

**Dashboard → [nsw-property-data.streamlit.app](https://nsw-property-data.streamlit.app/)**
**Data source → [NSW Valuer General](https://valuation.property.nsw.gov.au/embed/propertySalesInformation)**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           EventBridge — every Monday 10am AEDT              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │     file_selector     │
               │  Builds download list │
               │  (yearly 1990–now     │
               │   + latest weekly)    │
               └───────────┬───────────┘
                           │  Async invoke × N files
                           ▼
               ┌───────────────────────┐
               │    file_downloader    │
               │  Downloads ZIPs from  │
               │  NSW Valuer General   │
               └───────────┬───────────┘
                           │  Saves to S3 → async invoke
                           ▼
               ┌───────────────────────┐
               │      zip_scanner      │
               │  Recursively unpacks  │
               │  nested ZIPs, finds   │
               │  all .dat files       │
               └───────────┬───────────┘
                           │  1 SQS message per .dat file
                           ▼
               ┌───────────────────────┐
               │      db_ingestor      │
               │  Parses .dat lines    │
               │  Batch inserts 1,000  │
               │  records per txn      │
               └───────────┬───────────┘
                           │  On failure (after 1 retry)
                    ┌──────┴──────┐
                    ▼             ▼
              RDS PostgreSQL    Dead Letter
              (PostgreSQL 16)   Queue (14d)
                    │
                    ▼
    ┌─────────────────────────────────────┐
    │         Database Layers             │
    │                                     │
    │  nsw_property_sales_raw             │  ← raw .dat records
    │      ↓                              │
    │  vw_nsw_property_sales              │  ← normalised view
    │      ↓                              │
    │  mv_nsw_property_sales              │  ← materialized snapshot
    │      ↓                              │
    │  mv_stats_agg                       │  ┐
    │  mv_quarterly_agg                   │  ├─ pre-aggregated for dashboard
    │  mv_suburb_agg                      │  ┘
    └─────────────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────┐
    │   Streamlit Dashboard               │
    │   nsw-property-data.streamlit.app   │
    │   Parallel queries · 10min cache    │
    └─────────────────────────────────────┘
```

---

## Stack

| Layer | Tech |
|---|---|
| Pipeline | AWS Lambda (Python 3.12) × 4 functions |
| Storage | S3 (raw ZIPs + .dat files) |
| Queue | SQS + DLQ |
| Database | RDS PostgreSQL 16 (t3.micro) |
| Dashboard | Streamlit Cloud + Plotly |
| IaC | Terraform |
| Scheduler | EventBridge cron |

---

## Database

Raw `.dat` records land in `nsw_property_sales_raw` as-is. The normalised view `vw_nsw_property_sales` parses the semicolon-delimited lines, handles two historical formats (pre/post 2001 field layouts), constructs full addresses, and derives `property_type` (House vs Unit) from unit and strata fields.

Three pre-aggregated materialized views sit on top and power the dashboard queries:

| View | Grain | Used for |
|---|---|---|
| `mv_stats_agg` | year + postcode + type | KPI cards |
| `mv_quarterly_agg` | quarter + year + postcode + type | Volume + price trend charts |
| `mv_suburb_agg` | suburb + year + postcode + type | Top 10 suburbs chart |

Each stores `sales_count`, `price_sum`, and `median_price` so re-aggregation across any filter combination stays accurate. All four MVs are refreshed in sequence every Monday after ingestion completes.

---

## Dashboard

Filters by year, postcode, and property type. Three queries run in parallel via `ThreadPoolExecutor` and results are cached for 10 minutes.

- **KPIs** — total sales, average price, median price
- **Sale Volume by Quarter** — stacked bar (House vs Unit)
- **Median Price by Quarter** — dual-line trend
- **Top 10 Suburbs** — horizontal stacked bar
- **Recent 50 Sales** — transaction table with address, price, area, and dates

---

## Repo Structure

```
├── functions/          4 Lambda handlers + shared requirements
├── database/           schema, materialized views, indexes, refresh scripts
├── streamlit/          dashboard.py, queries.py, db.py
└── terraform/          all AWS infrastructure as code
```

---

## Deploy

```bash
cd terraform
terraform init && terraform apply
```

Creates: 4 Lambdas, RDS instance, S3 bucket, SQS + DLQ, EventBridge rule, CloudWatch dashboard, Lambda layer.


## Overview

This project downloads, processes, and stores all NSW property sales records dating back to 1990. Data is sourced from the NSW Valuer General website, extracted from nested ZIP archives, parsed from `.dat` files, and loaded into a structured PostgreSQL database. The pipeline runs automatically every Monday and keeps the database up to date with the latest weekly release.

---

## Cloud Technology

| Service | Purpose |
|---|---|
| **AWS Lambda (Python 3.12)** | 4 serverless functions driving the entire pipeline |
| **AWS RDS (PostgreSQL 16)** | Stores all property sales records |
| **AWS S3** | Stores downloaded ZIP files and extracted `.dat` files |
| **AWS SQS** | Decouples ZIP scanning from database ingestion |
| **AWS CloudWatch Events** | Weekly cron trigger (Monday 10am AEDT) |
| **AWS CloudWatch Dashboard** | Monitors Lambda errors and invocations |
| **Terraform** | Infrastructure as Code for all AWS resources |

---

## Architecture & Full Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                  CloudWatch Event Rule                           │
│              cron(0 0 ? * MON *)  — Monday 10am AEDT            │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │     file_selector     │
              │  Generates task list  │
              │  (yearly 1990–now +   │
              │   weekly files)       │
              └───────────┬───────────┘
                          │  Async Lambda Invoke (×N files)
                          ▼
              ┌───────────────────────┐
              │    file_downloader    │
              │  Downloads .zip from  │
              │  NSW Valuer General   │
              │  → Stores in S3       │
              └───────────┬───────────┘
                          │  Async Lambda Invoke
                          ▼
              ┌───────────────────────┐
              │      zip_scanner      │
              │  Recursively extracts │
              │  .dat files from ZIPs │
              │  → Sends SQS messages │
              └───────────┬───────────┘
                          │  SQS Event Source Mapping
                          │  (max 10 concurrent)
                          ▼
              ┌───────────────────────┐
              │      db_ingestor      │
              │  Parses .dat records  │
              │  Batch inserts into   │
              │  RDS PostgreSQL       │
              └───────────┬───────────┘
                          │
                          ▼
         ┌─────────────────────────────────┐
         │   PostgreSQL (AWS RDS)          │
         │   nsw_property_sales_raw        │  ← raw ingestion table
         │   vw_nsw_property_sales         │  ← normalised view
         └─────────────────────────────────┘
```

### Error Handling

```
db_ingestor failure
        │
        ▼ (after 1 retry)
┌──────────────────────┐
│   Dead Letter Queue   │
│  (14-day retention)  │
└──────────────────────┘
```

---

## Folder Structure

```
NSW-property-data/
├── database/
│   └── schema.sql                  # PostgreSQL table + view definitions
│
├── functions/
│   ├── requirements.txt            # Python dependencies (pg8000)
│   ├── file_selector/
│   │   └── handler.py              # Lambda: generates download task list
│   ├── file_downloader/
│   │   └── handler.py              # Lambda: downloads ZIPs from Valuer General
│   ├── zip_scanner/
│   │   └── handler.py              # Lambda: extracts .dat files, sends to SQS
│   └── db_ingestor/
│       └── handler.py              # Lambda: parses + batch inserts into RDS
│
└── terraform/
    ├── main.tf                     # AWS provider configuration
    ├── variables.tf                # Input variable definitions
    ├── terraform.tfvars            # Variable values (credentials — gitignored)
    ├── lambdas.tf                  # Lambda functions, IAM roles, CloudWatch trigger
    ├── database.tf                 # RDS PostgreSQL instance
    ├── storage.tf                  # S3 bucket
    ├── queues.tf                   # SQS ingestion queue + DLQ
    ├── layer.tf                    # Lambda layer (Python dependencies)
    ├── dashboard.tf                # CloudWatch monitoring dashboard
    └── outputs.tf                  # Output values (endpoints, ARNs)
```

---

## Lambda Functions

### 1. `file_selector`
- **Trigger**: CloudWatch cron — every Monday at 0:00 UTC (10am Sydney)
- **Purpose**: Determines which files need to be downloaded
- **Modes**: `full` (all years 1990–present) or `last_week` (default, latest weekly file only)
- **Output**: Asynchronously invokes `file_downloader` for each file task

### 2. `file_downloader`
- **Trigger**: Async invocation from `file_selector`
- **Purpose**: Downloads ZIP files from `https://www.valuergeneral.nsw.gov.au/__psi/`
- **Output**: Saves to `s3://nsw-property-data/NSW/Download/{yearly|weekly}/`, then invokes `zip_scanner`

### 3. `zip_scanner`
- **Trigger**: Async invocation from `file_downloader`
- **Purpose**: Recursively opens nested ZIP archives and locates all `.dat` files
- **Output**: Sends one SQS message per `.dat` file with `{ bucket, key }`

### 4. `db_ingestor`
- **Trigger**: SQS event source mapping (max 10 concurrent executions)
- **Purpose**: Downloads `.dat` file from S3, parses line-by-line, batch inserts into RDS
- **Batch size**: 1,000 records per INSERT
- **Error handling**: Rolls back transaction on failure; SQS retries once before DLQ

---

## S3 Structure

```
s3://nsw-property-data/
└── NSW/
    └── Download/
        ├── yearly/
        │   ├── 1990.zip
        │   ├── 1991.zip
        │   └── ... (up to current year)
        └── weekly/
            ├── 20240101.zip
            └── ... (latest weekly files)
```

---

## Database

**Engine**: PostgreSQL 16 on AWS RDS (t3.micro, 20GB)

### Table: `nsw_property_sales_raw`

Raw ingestion table — each row stores one complete `.dat` record as-is.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL PRIMARY KEY | Auto-incrementing row ID |
| `row_number` | INTEGER | Line number within source file |
| `raw_line` | TEXT | Full raw record (semicolon-delimited) |
| `source_file` | TEXT | S3 path to the source `.dat` file |
| `ingested_at` | TIMESTAMP | UTC timestamp of ingestion |

### View: `vw_nsw_property_sales`

Normalised view that parses `raw_line` into structured columns. Supports two historical data formats automatically (field count determines format).

**Identifiers**

| Column | Description |
|---|---|
| `district_code` | NSW land district code |
| `property_id` | Unique property identifier |
| `sale_counter` | Sale transaction counter |
| `file_format` | `current_2001_to_present` or `archived_1990_to_2001` |

**Property & Address**

| Column | Description |
|---|---|
| `property_name` | Official property name |
| `unit_number` | Unit/apartment number |
| `house_number` | Street number |
| `street_name` | Street name |
| `suburb` | Suburb/locality |
| `post_code` | Postal code |
| `full_address` | Constructed address (e.g. `Unit 3, 82 Tamworth St, Abermain NSW 2326`) |

**Dates**

| Column | Type | Description |
|---|---|---|
| `contract_date` | DATE | Contract date (handles DD/MM/YYYY and YYYYMMDD) |
| `settlement_date` | DATE | Settlement date |

**Financials & Land**

| Column | Type | Description |
|---|---|---|
| `purchase_price` | NUMERIC | Sale price in AUD |
| `area` | NUMERIC | Property area/size |
| `area_type` | TEXT | Unit of area (e.g. square meters) |
| `dimensions` | TEXT | Property dimensions (archived format only) |
| `land_description` | TEXT | Land description (archived format only) |

**Classification**

| Column | Description |
|---|---|
| `zone_code` | Zoning classification |
| `nature_of_property` | Property type (residential, commercial, etc.) |
| `primary_purpose` | Intended use |
| `strata_lot_number` | Strata lot identifier |

**Sale Details**

| Column | Description |
|---|---|
| `sale_code` | Sale transaction code |
| `percent_interest_of_sale` | Percentage interest sold (defaults to 100) |
| `dealing_number` | Land dealings reference number |

---

## Monitoring

A CloudWatch Dashboard (`NSWPropertyDataPipeline`) tracks the following metrics across all 4 Lambda functions:

- **Errors** — total error count per function
- **Invocations** — total invocation count per function

---

## Infrastructure (Terraform)

All AWS resources are defined in Terraform under `terraform/`. To deploy:

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Key resources created:
- 4 Lambda functions with IAM roles and policies
- 1 RDS PostgreSQL instance
- 1 S3 bucket
- 2 SQS queues (main + DLQ)
- 1 CloudWatch Event Rule (weekly cron)
- 1 CloudWatch Dashboard
- 1 Lambda Layer (Python dependencies)

---

## Future Plans — Property Dashboard

The next phase of this project is to build an interactive **property data dashboard** hosted on an **AWS EC2 instance**, built entirely in Python.

### Planned Stack

| Component | Technology |
|---|---|
| **Dashboard framework** | Plotly Dash or Streamlit |
| **Database connection** | psycopg2 / SQLAlchemy → RDS PostgreSQL |
| **Hosting** | AWS EC2 (Python web server) |
| **Reverse proxy** | Nginx |
| **Process manager** | systemd or PM2 |

### Planned Features

- **Interactive map** — choropleth or scatter map of property sales across NSW suburbs
- **Price trends** — historical median sale price by suburb, property type, or zone
- **Sales volume charts** — weekly/monthly/yearly transaction counts
- **Filter controls** — filter by suburb, postcode, date range, property type, sale price
- **Top suburbs** — ranked list by median price, volume, or price growth
- **Raw data table** — searchable, sortable view of individual transactions
- **Download** — export filtered results to CSV

### Architecture (Planned)

```
User Browser
     │
     ▼
EC2 Instance (Python Dash App)
     │
     ▼
AWS RDS PostgreSQL
(vw_nsw_property_sales)
```

The EC2 instance will query the existing RDS database directly, so no additional data infrastructure is needed — the pipeline already keeps the data fresh every Monday.

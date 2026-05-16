# U.S. Used Vehicle Market Intelligence Pipeline

An end-to-end AWS data pipeline analyzing pricing dynamics, regional demand, and deal quality across 366,000+ U.S. used vehicle listings — built to understand the Amazon Autos problem space.

## Architecture

Raw Data (S3) → AWS Glue ETL (PySpark) → Transformed Data (S3/Parquet) → Athena (SQL) → Tableau Dashboard

**Three-zone S3 structure:**
- `raw/` — original Craigslist dataset, untouched
- `transformed/` — cleaned, enriched, KPI-annotated Parquet files partitioned by state
- `error/` — records that failed validation with a specific reason flag

## Pipeline Components

### AWS Glue ETL (`autos_etl.py`)
PySpark job that runs across 2 G.1X workers and performs:
- **Cleaning** — standardizes casing, trims whitespace, casts columns to correct types
- **Validation** — evaluates 11 business rules, routes ~33k bad records to error zone with reason flags
- **Enrichment** — derives vehicle age, price per mile, age brackets, mileage buckets
- **KPI computation** — 5 window functions computing depreciation curves, regional demand, condition premiums, mileage discounts, and deal quality scores
- **Loading** — writes clean data as Parquet partitioned by state, errors as CSV

### Amazon Athena (`athena_queries.sql`)
5 analytical SQL queries using CTEs and window functions:
1. **Price depreciation** — avg price by manufacturer and age bracket
2. **Regional demand** — listing volume and avg price ranked by state
3. **Condition premium** — price impact of vehicle condition within each brand
4. **Mileage discount curve** — price drop per mileage bucket by manufacturer
5. **Deal depth** — avg % below market median for underpriced listings by state

### Tableau Dashboard
4-chart dashboard connected to Athena query outputs:
- Price depreciation curves by manufacturer
- Regional demand ranked by state
- Deal depth by state (discount depth, not just volume)
- Condition premium by manufacturer

## Key Findings
- **366,739 clean records** processed from ~400k raw listings
- **California** leads in listing volume but ranks 28th in deal depth — lots of inventory, shallow discounts
- **Maine and Oregon** have the deepest discounts averaging 63-64% below local market median
- **Ferrari** commands the largest condition premium — "like new" inventory averages ~$190k vs ~$80k for "fair"
- Regional pricing varies significantly for identical make/model combinations across states

## Tech Stack
- **AWS S3** — three-zone data lake architecture
- **AWS Glue** — managed PySpark ETL
- **AWS Athena** — serverless SQL query layer
- **Apache Spark / PySpark** — distributed data transformation
- **Tableau** — business intelligence dashboard
- **Python** — pipeline scripting

## Dataset
Craigslist Used Cars dataset via Kaggle (~400k listings, 1.4GB)

# U.S. Used Vehicle Market Intelligence Pipeline

An end-to-end AWS data pipeline analyzing pricing dynamics, regional demand, and deal quality across 366,000+ U.S. used vehicle listings — built to understand the Amazon Autos problem space.

## Architecture

Raw Data (S3) → AWS Glue ETL (PySpark) → Transformed Data (S3/Parquet) → Athena (SQL) → Power BI Dashboard

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

### Business Analysis Notebook (`notebooks/vehicle_market_analysis.ipynb`)
boto3 + pandas notebook that executes all 8 business queries against Athena and produces:
- Depreciation multi-line chart per manufacturer
- Sweet spot heatmap (age × mileage → % of benchmark)
- Regional arbitrage horizontal bar chart
- Condition premium grouped bar chart
- Market concentration scatter (inventory rank vs price rank)
- Deal quality stacked bar chart
- Outlier z-score strip plot
- Duplicate analysis charts

Charts are saved to `charts/` for use in presentations or the Power BI dashboard.

### Power BI Dashboard (`powerbi/UsedVehicleMarket.pbit`)
4-page interactive dashboard built on the 8 business query outputs:
- **Depreciation & Value** — multi-line depreciation curves by manufacturer + data table
- **Deal Finder** — sweet spot matrix (age × mileage) + deal quality bar chart
- **Regional Intelligence** — arbitrage bar chart (% vs national median) + inventory/price scatter
- **Inventory Quality** — condition premium column chart + outlier z-score table + duplicate listings bar

Built as a Power BI Template (`.pbit`) using `powerbi/build_pbit.py` — runs `powerbi/export_data.py` first to pull fresh query results from Athena to `powerbi/data/`, then `build_pbit.py` packages the model + report into the template file.

**Tech:** Power BI Desktop, Power Query M, DAX-compatible tabular model, Amazon Athena ODBC + CSV export path

## Key Findings
- **366,739 clean records** processed from ~400k raw listings
- **California** leads in listing volume but ranks 28th in deal depth — lots of inventory, shallow discounts
- **Maine and Oregon** have the deepest discounts averaging 63-64% below local market median
- **Ferrari** commands the largest condition premium — "like new" inventory averages ~$190k vs ~$80k for "fair"
- Regional pricing varies significantly for identical make/model combinations across states

## Business Analysis (`queries/business_analysis.sql` + `notebooks/vehicle_market_analysis.ipynb`)

Eight additional Athena queries go beyond descriptive stats to answer operational business questions:

| # | Query | Business Question |
|---|-------|-------------------|
| 1 | Depreciation Curve | Which manufacturers hold value best across vehicle age? |
| 2 | Sweet Spot Analysis | What age/mileage combo consistently delivers below-benchmark pricing? |
| 3 | Regional Arbitrage | Which state/make combos are >15% below national median — cross-state sourcing opportunities? |
| 4 | Condition Premium | How much does "excellent" vs "fair" condition actually cost per manufacturer? |
| 5 | Market Concentration | Do high-inventory states have lower prices, or does demand override supply? |
| 6 | Deal Quality Distribution | Which manufacturer/state combos have the densest concentration of underpriced inventory? |
| 7 | Price Outlier Detection | Which listings are statistically anomalous vs their cohort (z-score > ±2)? |
| 8 | Duplicate Detection | How much of apparent inventory is re-listed supply inflating market size? |

### Strategic Recommendations

**For buyers:**
- Target the **8-12 year / 100-150k mile** bracket — this cohort consistently prices below benchmark with the highest concentration of great deals, representing the market's genuine value zone.
- Prioritize sourcing in states identified by Query 3 — the same make can be 15-25% cheaper than the national median in low-competition states, with the spread often exceeding transport cost.
- Use condition premiums (Query 4) as a negotiation anchor: for mainstream brands the excellent-to-fair spread is modest, but for luxury and performance brands the gap is large enough that buying "good" instead of "excellent" condition can save more than a full year of ownership costs.

**For dealers:**
- Query 6's opportunity_rank metric surfaces the specific state/make combinations where underpriced inventory is most concentrated — these are your acquisition targets, not just your highest-volume markets.
- High inventory/high price states (warm-colored in Query 5's scatter) signal strong underlying demand — pricing can hold firm here even at above-median volumes.
- Flag listings identified by Query 7's z-score < -2 for immediate review: these are either genuine bargains to acquire quickly or data quality issues to audit before using in benchmarks.
- Query 8's duplicate detection matters for supply/demand modeling — overstated listing counts will inflate perceived market supply and cause you to underestimate true demand tightness.

## Tech Stack
- **AWS S3** — three-zone data lake architecture
- **AWS Glue** — managed PySpark ETL
- **AWS Athena** — serverless SQL query layer
- **Apache Spark / PySpark** — distributed data transformation
- **Power BI Desktop** — interactive 4-page dashboard (.pbit template)
- **Python** — pipeline scripting + PBIT build tooling

## Dataset
Craigslist Used Cars dataset via Kaggle (~400k listings, 1.4GB)

import boto3, pandas as pd, time, os

DATABASE        = "autos_db"
OUTPUT_LOCATION = "s3://norman-autos-pipeline/athena-results/"
REGION          = "us-east-1"
OUT_DIR         = r"C:\Users\norma\used-vehicle-market-pipeline\powerbi\data"

os.makedirs(OUT_DIR, exist_ok=True)
athena = boto3.client("athena", region_name=REGION)

def run_query(sql, label):
    resp = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": DATABASE},
        ResultConfiguration={"OutputLocation": OUTPUT_LOCATION},
    )
    qid = resp["QueryExecutionId"]
    while True:
        state = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1.5)
    if state != "SUCCEEDED":
        print(f"FAILED: {label}")
        return
    pager = athena.get_paginator("get_query_results")
    rows, cols = [], None
    for page in pager.paginate(QueryExecutionId=qid):
        rs = page["ResultSet"]
        if cols is None:
            cols = [c["Label"] for c in rs["ResultSetMetadata"]["ColumnInfo"]]
        for row in rs["Rows"][1 if cols and not rows else 0:]:
            rows.append([d.get("VarCharValue") for d in row["Data"]])
    df = pd.DataFrame(rows, columns=cols)
    path = os.path.join(OUT_DIR, f"{label}.csv")
    df.to_csv(path, index=False)
    print(f"Saved {label}.csv  ({len(df)} rows)")

QUERIES = {
    "q1_depreciation": """
        SELECT manufacturer, age_bracket, COUNT(*) AS listing_count,
          ROUND(AVG(price),0) AS avg_price,
          ROUND(AVG(price)/NULLIF(AVG(avg_price_by_make_age),0)*100,1) AS pct_of_benchmark,
          ROUND(AVG(price_per_mile),4) AS avg_price_per_mile
        FROM autos_db.vehicles_view
        WHERE price>0 AND manufacturer IS NOT NULL AND avg_price_by_make_age>0
        GROUP BY manufacturer,age_bracket HAVING COUNT(*)>=10
        ORDER BY manufacturer,age_bracket""",

    "q2_sweet_spot": """
        SELECT age_bracket, mileage_bucket, COUNT(*) AS listing_count,
          ROUND(AVG(price),0) AS avg_price,
          ROUND(AVG(price)/NULLIF(AVG(avg_price_by_make_age),0)*100,1) AS avg_pct_of_benchmark,
          SUM(CASE WHEN deal_quality='great_deal' THEN 1 ELSE 0 END) AS great_deal_count,
          ROUND(SUM(CASE WHEN deal_quality='great_deal' THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS great_deal_pct
        FROM autos_db.vehicles_view WHERE price>0
        GROUP BY age_bracket,mileage_bucket HAVING COUNT(*)>=20
        ORDER BY avg_pct_of_benchmark ASC""",

    "q3_arbitrage": """
        WITH nm AS (
          SELECT manufacturer, APPROX_PERCENTILE(price,0.5) AS national_median_price
          FROM autos_db.vehicles_view WHERE price>0 AND manufacturer IS NOT NULL
          GROUP BY manufacturer HAVING COUNT(*)>=50),
        ss AS (
          SELECT state,manufacturer,ROUND(AVG(price),0) AS state_avg_price,COUNT(*) AS state_count
          FROM autos_db.vehicles_view WHERE price>0 AND manufacturer IS NOT NULL
          GROUP BY state,manufacturer HAVING COUNT(*)>=5)
        SELECT s.state,s.manufacturer,s.state_avg_price,
          ROUND(n.national_median_price,0) AS national_median_price,
          ROUND((s.state_avg_price-n.national_median_price)/n.national_median_price*100,1) AS pct_vs_national,
          s.state_count
        FROM ss s JOIN nm n ON s.manufacturer=n.manufacturer
        WHERE s.state_avg_price < n.national_median_price*0.85
        ORDER BY pct_vs_national ASC LIMIT 30""",

    "q4_condition": """
        SELECT manufacturer,condition,COUNT(*) AS listing_count,
          ROUND(AVG(price),0) AS avg_price,
          ROUND(AVG(price)/NULLIF(AVG(AVG(price)) OVER (PARTITION BY manufacturer),0)*100,1) AS pct_of_make_avg
        FROM autos_db.vehicles_view
        WHERE price>0 AND manufacturer IS NOT NULL AND condition IS NOT NULL AND condition!=''
        GROUP BY manufacturer,condition HAVING COUNT(*)>=10
        ORDER BY manufacturer,avg_price DESC""",

    "q5_market_concentration": """
        SELECT state,COUNT(*) AS total_listings,ROUND(AVG(price),0) AS avg_price,
          ROUND(APPROX_PERCENTILE(price,0.5),0) AS median_price,
          SUM(CASE WHEN deal_quality='great_deal' THEN 1 ELSE 0 END) AS great_deals,
          ROUND(SUM(CASE WHEN deal_quality='great_deal' THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS great_deal_pct,
          RANK() OVER (ORDER BY COUNT(*) DESC) AS inventory_rank,
          RANK() OVER (ORDER BY AVG(price) ASC) AS price_rank
        FROM autos_db.vehicles_view WHERE price>0 AND state IS NOT NULL
        GROUP BY state,state_listing_count HAVING COUNT(*)>=50
        ORDER BY total_listings DESC""",

    "q6_deal_quality": """
        SELECT manufacturer,state,COUNT(*) AS total_listings,
          SUM(CASE WHEN deal_quality='great_deal' THEN 1 ELSE 0 END) AS great_deals,
          SUM(CASE WHEN deal_quality='good_deal'  THEN 1 ELSE 0 END) AS good_deals,
          SUM(CASE WHEN deal_quality='fair'        THEN 1 ELSE 0 END) AS fair_deals,
          SUM(CASE WHEN deal_quality='overpriced'  THEN 1 ELSE 0 END) AS overpriced,
          ROUND(SUM(CASE WHEN deal_quality IN ('great_deal','good_deal') THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS pct_good_or_better
        FROM autos_db.vehicles_view
        WHERE price>0 AND manufacturer IS NOT NULL AND state IS NOT NULL
        GROUP BY manufacturer,state HAVING COUNT(*)>=10
        ORDER BY pct_good_or_better DESC LIMIT 40""",

    "q7_outliers": """
        WITH cs AS (
          SELECT manufacturer,age_bracket,mileage_bucket,
            AVG(price) AS cohort_avg,STDDEV(price) AS cohort_stddev,COUNT(*) AS cohort_size
          FROM autos_db.vehicles_view WHERE price>0 AND manufacturer IS NOT NULL
          GROUP BY manufacturer,age_bracket,mileage_bucket HAVING COUNT(*)>=5)
        SELECT v.manufacturer,v.state,v.price,v.condition,v.vehicle_age,v.odometer,
          ROUND(c.cohort_avg,0) AS cohort_avg_price,
          ROUND((v.price-c.cohort_avg)/NULLIF(c.cohort_stddev,0),2) AS z_score,
          CASE WHEN (v.price-c.cohort_avg)/NULLIF(c.cohort_stddev,0)<-2 THEN 'significant_bargain'
               WHEN (v.price-c.cohort_avg)/NULLIF(c.cohort_stddev,0)>2  THEN 'significant_outlier'
               ELSE 'normal' END AS outlier_flag
        FROM autos_db.vehicles_view v
        JOIN cs c ON v.manufacturer=c.manufacturer AND v.age_bracket=c.age_bracket AND v.mileage_bucket=c.mileage_bucket
        WHERE price>0 AND ABS((v.price-c.cohort_avg)/NULLIF(c.cohort_stddev,0))>2
        ORDER BY z_score ASC LIMIT 50""",

    "q8_duplicates": """
        SELECT price,manufacturer,model,odometer,state,COUNT(*) AS duplicate_count
        FROM autos_db.vehicles_view WHERE price>0 AND manufacturer IS NOT NULL
        GROUP BY price,manufacturer,model,odometer,state HAVING COUNT(*)>1
        ORDER BY duplicate_count DESC LIMIT 30"""
}

for label, sql in QUERIES.items():
    run_query(sql, label)

print("All done.")

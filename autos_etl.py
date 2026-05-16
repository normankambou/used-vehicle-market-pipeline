import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.sql.window import Window
from datetime import date

# ── 1. SETUP ──────────────────────────────────────────────────────────────────
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# S3 paths — three-zone architecture
RAW_PATH         = "s3://norman-autos-pipeline/raw/vehicles.csv"
TRANSFORMED_PATH = "s3://norman-autos-pipeline/transformed/"
ERROR_PATH       = "s3://norman-autos-pipeline/error/"

print("✓ Setup complete")

# ── 2. EXTRACT ────────────────────────────────────────────────────────────────
# Read raw CSV from S3
df = spark.read.option("header", "true").option("inferSchema", "true").csv(RAW_PATH)

raw_count = df.count()
print(f"✓ Extracted {raw_count:,} records from raw zone")

# ── 3. CLEAN ──────────────────────────────────────────────────────────────────
# Standardize text casing on key categorical fields
df = df.withColumn("manufacturer", F.upper(F.trim(F.col("manufacturer")))) \
       .withColumn("model",        F.lower(F.trim(F.col("model")))) \
       .withColumn("condition",    F.lower(F.trim(F.col("condition")))) \
       .withColumn("fuel",         F.lower(F.trim(F.col("fuel")))) \
       .withColumn("title_status", F.lower(F.trim(F.col("title_status")))) \
       .withColumn("transmission", F.lower(F.trim(F.col("transmission")))) \
       .withColumn("state",        F.upper(F.trim(F.col("state"))))

# Cast numeric fields to correct types
df = df.withColumn("price",        F.col("price").cast(DoubleType())) \
       .withColumn("odometer",     F.col("odometer").cast(DoubleType())) \
       .withColumn("year",         F.col("year").cast(IntegerType()))

print("✓ Cleaning complete")

# ── 4. VALIDATE ───────────────────────────────────────────────────────────────
# Tag each record with a failure reason before splitting
# A record is bad if any critical field is null or outside reasonable bounds

current_year = date.today().year

df = df.withColumn("error_reason",
    F.when(F.col("price").isNull(),                          F.lit("null_price"))
     .when(F.col("price") <= 0,                             F.lit("zero_or_negative_price"))
     .when(F.col("price") > 150000,                         F.lit("price_exceeds_150k"))
     .when(F.col("odometer").isNull(),                      F.lit("null_odometer"))
     .when(F.col("odometer") <= 0,                          F.lit("zero_or_negative_odometer"))
     .when(F.col("odometer") > 500000,                      F.lit("odometer_exceeds_500k"))
     .when(F.col("year").isNull(),                          F.lit("null_year"))
     .when(F.col("year") < 1900,                            F.lit("year_before_1900"))
     .when(F.col("year") > current_year,                    F.lit("year_in_future"))
     .when(F.col("manufacturer").isNull(),                  F.lit("null_manufacturer"))
     .when(F.col("state").isNull(),                         F.lit("null_state"))
     .otherwise(F.lit(None))
)

# Split into clean and error DataFrames
df_clean = df.filter(F.col("error_reason").isNull()).drop("error_reason")
df_error  = df.filter(F.col("error_reason").isNotNull())

clean_count = df_clean.count()
error_count = df_error.count()

print(f"✓ Validation complete — {clean_count:,} clean | {error_count:,} errors")

# ── 5. ENRICH ─────────────────────────────────────────────────────────────────
# Derived fields that add analytical value beyond the raw data

df_clean = df_clean \
    .withColumn("vehicle_age",    F.lit(current_year) - F.col("year")) \
    .withColumn("price_per_mile", 
        F.when(F.col("odometer") > 0, F.round(F.col("price") / F.col("odometer"), 4))
         .otherwise(F.lit(None))) \
    .withColumn("age_bracket",
        F.when(F.col("vehicle_age") <= 3,  F.lit("0-3 years"))
         .when(F.col("vehicle_age") <= 7,  F.lit("4-7 years"))
         .when(F.col("vehicle_age") <= 12, F.lit("8-12 years"))
         .otherwise(F.lit("13+ years"))) \
    .withColumn("mileage_bucket",
        F.when(F.col("odometer") <= 30000,  F.lit("0-30k"))
         .when(F.col("odometer") <= 60000,  F.lit("30-60k"))
         .when(F.col("odometer") <= 100000, F.lit("60-100k"))
         .when(F.col("odometer") <= 150000, F.lit("100-150k"))
         .otherwise(F.lit("150k+")))

print("✓ Enrichment complete")

# ── 6. KPIs ───────────────────────────────────────────────────────────────────

# KPI 1: Price depreciation by manufacturer and age bracket
# Shows how much value each brand loses as vehicles age
w_depreciation = Window.partitionBy("manufacturer", "age_bracket")
df_clean = df_clean.withColumn(
    "avg_price_by_make_age",
    F.round(F.avg("price").over(w_depreciation), 2)
)

# KPI 2: Regional demand index
# Measures listing volume by state — proxy for regional supply/demand
w_regional = Window.partitionBy("state")
df_clean = df_clean.withColumn(
    "state_listing_count",
    F.count("*").over(w_regional)
)

# KPI 3: Condition premium
# How much extra does "excellent" condition add vs "good" within same make?
w_condition = Window.partitionBy("manufacturer", "condition")
df_clean = df_clean.withColumn(
    "avg_price_by_make_condition",
    F.round(F.avg("price").over(w_condition), 2)
)

# KPI 4: Mileage discount curve
# How much does price drop as mileage increases within each manufacturer?
w_mileage = Window.partitionBy("manufacturer", "mileage_bucket")
df_clean = df_clean.withColumn(
    "avg_price_by_make_mileage",
    F.round(F.avg("price").over(w_mileage), 2)
)

# KPI 5: Deal quality score
# Flags listings priced below the state median for same make — potential deals
w_state_make = Window.partitionBy("state", "manufacturer")
df_clean = df_clean \
    .withColumn("state_make_median_price",
        F.round(F.percentile_approx("price", 0.5).over(w_state_make), 2)) \
    .withColumn("deal_quality",
        F.when(F.col("price") < F.col("state_make_median_price") * 0.85, F.lit("great_deal"))
         .when(F.col("price") < F.col("state_make_median_price") * 0.95, F.lit("good_deal"))
         .when(F.col("price") < F.col("state_make_median_price") * 1.05, F.lit("fair"))
         .otherwise(F.lit("overpriced")))

print("✓ KPI computation complete")

# ── 7. LOAD ───────────────────────────────────────────────────────────────────
# Write clean transformed data to S3 transformed zone as Parquet
# Parquet is columnar format — much faster for Athena to query than CSV
df_clean.write \
    .mode("overwrite") \
    .partitionBy("state") \
    .parquet(TRANSFORMED_PATH)

# Write error records to error zone as CSV for easy inspection
df_error.write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv(ERROR_PATH)

print(f"✓ Load complete — {clean_count:,} records written to transformed zone")
print(f"✓ {error_count:,} error records written to error zone")

job.commit()
print("✓ Job committed successfully")

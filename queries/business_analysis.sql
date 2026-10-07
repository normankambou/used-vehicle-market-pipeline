-- ============================================================
-- U.S. Used Vehicle Market — Business Analysis Queries
-- Database: autos_db | View: vehicles_view
-- All queries confirmed working in Amazon Athena
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- QUERY 1: Depreciation Curve by Manufacturer
-- Business question: Which manufacturers hold their value best
--   as vehicles age?
-- Use case: Helps buyers and dealers identify which brands
--   command premium resale value across the vehicle lifecycle.
-- Key fields: age_bracket (derived), avg_price_by_make_age (KPI)
-- ────────────────────────────────────────────────────────────
SELECT
  manufacturer,
  age_bracket,
  COUNT(*) AS listing_count,
  ROUND(AVG(price), 0) AS avg_price,
  ROUND(AVG(price) / NULLIF(AVG(avg_price_by_make_age), 0) * 100, 1) AS pct_of_benchmark,
  ROUND(AVG(price_per_mile), 4) AS avg_price_per_mile
FROM autos_db.vehicles_view
WHERE price > 0
  AND manufacturer IS NOT NULL
  AND avg_price_by_make_age > 0
GROUP BY manufacturer, age_bracket
HAVING COUNT(*) >= 10
ORDER BY manufacturer, age_bracket;


-- ────────────────────────────────────────────────────────────
-- QUERY 2: Sweet Spot Analysis — Best Value by Age and Mileage
-- Business question: What age/mileage combination delivers the
--   best price-to-market ratio?
-- Use case: Actionable inventory acquisition guidance for
--   dealers — points to cohorts consistently priced below
--   benchmark with a high concentration of great deals.
-- Key fields: age_bracket, mileage_bucket, deal_quality (KPI)
-- ────────────────────────────────────────────────────────────
SELECT
  age_bracket,
  mileage_bucket,
  COUNT(*) AS listing_count,
  ROUND(AVG(price), 0) AS avg_price,
  ROUND(AVG(price) / NULLIF(AVG(avg_price_by_make_age), 0) * 100, 1) AS avg_pct_of_benchmark,
  SUM(CASE WHEN deal_quality = 'great_deal' THEN 1 ELSE 0 END) AS great_deal_count,
  ROUND(SUM(CASE WHEN deal_quality = 'great_deal' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS great_deal_pct
FROM autos_db.vehicles_view
WHERE price > 0
GROUP BY age_bracket, mileage_bucket
HAVING COUNT(*) >= 20
ORDER BY avg_pct_of_benchmark ASC;


-- ────────────────────────────────────────────────────────────
-- QUERY 3: Regional Arbitrage Opportunities
-- Business question: Where is the same manufacturer selling
--   significantly cheaper than the national median?
-- Use case: Identifies states where dealers or buyers can
--   source inventory at below-market prices — cross-state
--   arbitrage potential.
-- Threshold: States where avg price is >15% below national
--   median for the same manufacturer (pct_vs_national < -15%)
-- ────────────────────────────────────────────────────────────
WITH national_median AS (
  SELECT
    manufacturer,
    APPROX_PERCENTILE(price, 0.5) AS national_median_price,
    COUNT(*) AS national_count
  FROM autos_db.vehicles_view
  WHERE price > 0 AND manufacturer IS NOT NULL
  GROUP BY manufacturer
  HAVING COUNT(*) >= 50
),
state_stats AS (
  SELECT
    state,
    manufacturer,
    ROUND(AVG(price), 0) AS state_avg_price,
    COUNT(*) AS state_count
  FROM autos_db.vehicles_view
  WHERE price > 0 AND manufacturer IS NOT NULL
  GROUP BY state, manufacturer
  HAVING COUNT(*) >= 5
)
SELECT
  s.state,
  s.manufacturer,
  s.state_avg_price,
  ROUND(n.national_median_price, 0) AS national_median_price,
  ROUND((s.state_avg_price - n.national_median_price) / n.national_median_price * 100, 1) AS pct_vs_national,
  s.state_count
FROM state_stats s
JOIN national_median n ON s.manufacturer = n.manufacturer
WHERE s.state_avg_price < n.national_median_price * 0.85
ORDER BY pct_vs_national ASC
LIMIT 30;


-- ────────────────────────────────────────────────────────────
-- QUERY 4: Condition Premium Analysis
-- Business question: How much extra does "excellent" condition
--   actually cost vs "good" or "fair"?
-- Use case: Helps buyers decide whether condition upgrades are
--   worth the premium on a per-manufacturer basis. Luxury
--   brands show disproportionately large condition gaps.
-- Key fields: condition, avg_price_by_make_condition (KPI)
-- ────────────────────────────────────────────────────────────
SELECT
  manufacturer,
  condition,
  COUNT(*) AS listing_count,
  ROUND(AVG(price), 0) AS avg_price,
  ROUND(AVG(price) / NULLIF(
    AVG(AVG(price)) OVER (PARTITION BY manufacturer), 0) * 100, 1
  ) AS pct_of_make_avg
FROM autos_db.vehicles_view
WHERE price > 0
  AND manufacturer IS NOT NULL
  AND condition IS NOT NULL
  AND condition != ''
GROUP BY manufacturer, condition
HAVING COUNT(*) >= 10
ORDER BY manufacturer, avg_price DESC;


-- ────────────────────────────────────────────────────────────
-- QUERY 5: Market Concentration and Price Elasticity by State
-- Business question: Do states with more inventory have lower
--   prices? Does supply actually depress price?
-- Use case: Identifies buyer-friendly markets (high inventory,
--   lower prices) vs seller-friendly markets (high inventory,
--   prices remain elevated — signal of strong underlying demand).
-- Key metric: inventory_rank vs price_rank divergence
-- ────────────────────────────────────────────────────────────
SELECT
  state,
  COUNT(*) AS total_listings,
  state_listing_count,
  ROUND(AVG(price), 0) AS avg_price,
  ROUND(APPROX_PERCENTILE(price, 0.5), 0) AS median_price,
  SUM(CASE WHEN deal_quality = 'great_deal' THEN 1 ELSE 0 END) AS great_deals,
  ROUND(SUM(CASE WHEN deal_quality = 'great_deal' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS great_deal_pct,
  RANK() OVER (ORDER BY COUNT(*) DESC) AS inventory_rank,
  RANK() OVER (ORDER BY AVG(price) ASC) AS price_rank
FROM autos_db.vehicles_view
WHERE price > 0 AND state IS NOT NULL
GROUP BY state, state_listing_count
HAVING COUNT(*) >= 50
ORDER BY total_listings DESC;


-- ────────────────────────────────────────────────────────────
-- QUERY 6: Deal Quality Distribution by Manufacturer and State
-- Business question: Which manufacturer/state combinations have
--   the highest concentration of underpriced inventory?
-- Use case: Sourcing intelligence for dealers looking for
--   acquisition opportunities — ranks combos by great deal
--   density within each state.
-- Key field: deal_quality (KPI, 4 tiers: great/good/fair/overpriced)
-- ────────────────────────────────────────────────────────────
SELECT
  manufacturer,
  state,
  COUNT(*) AS total_listings,
  SUM(CASE WHEN deal_quality = 'great_deal' THEN 1 ELSE 0 END) AS great_deals,
  SUM(CASE WHEN deal_quality = 'good_deal' THEN 1 ELSE 0 END) AS good_deals,
  SUM(CASE WHEN deal_quality = 'fair' THEN 1 ELSE 0 END) AS fair_deals,
  SUM(CASE WHEN deal_quality = 'overpriced' THEN 1 ELSE 0 END) AS overpriced,
  ROUND(SUM(CASE WHEN deal_quality IN ('great_deal','good_deal') THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_good_or_better,
  RANK() OVER (PARTITION BY state ORDER BY SUM(CASE WHEN deal_quality = 'great_deal' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) DESC) AS opportunity_rank
FROM autos_db.vehicles_view
WHERE price > 0
  AND manufacturer IS NOT NULL
  AND state IS NOT NULL
GROUP BY manufacturer, state
HAVING COUNT(*) >= 10
ORDER BY pct_good_or_better DESC
LIMIT 40;


-- ────────────────────────────────────────────────────────────
-- QUERY 7: Price Outlier Detection
-- Business question: Which listings are priced anomalously vs
--   their cohort (same make, age bracket, mileage bucket)?
-- Use case: (1) Flags potential data quality issues for audit.
--   (2) Identifies genuine bargains (z < -2) for automated
--   deal-alert systems. Cohort size >= 5 ensures statistical
--   reliability of z-score.
-- Output: Top 50 most extreme outliers, both high and low
-- ────────────────────────────────────────────────────────────
WITH cohort_stats AS (
  SELECT
    manufacturer,
    age_bracket,
    mileage_bucket,
    AVG(price) AS cohort_avg,
    STDDEV(price) AS cohort_stddev,
    COUNT(*) AS cohort_size
  FROM autos_db.vehicles_view
  WHERE price > 0 AND manufacturer IS NOT NULL
  GROUP BY manufacturer, age_bracket, mileage_bucket
  HAVING COUNT(*) >= 5
)
SELECT
  v.manufacturer,
  v.state,
  v.price,
  v.condition,
  v.vehicle_age,
  v.odometer,
  v.deal_quality,
  ROUND(c.cohort_avg, 0) AS cohort_avg_price,
  ROUND(c.cohort_stddev, 0) AS cohort_stddev,
  ROUND((v.price - c.cohort_avg) / NULLIF(c.cohort_stddev, 0), 2) AS z_score,
  CASE
    WHEN (v.price - c.cohort_avg) / NULLIF(c.cohort_stddev, 0) < -2 THEN 'significant_bargain'
    WHEN (v.price - c.cohort_avg) / NULLIF(c.cohort_stddev, 0) > 2 THEN 'significant_outlier'
    ELSE 'normal'
  END AS outlier_flag
FROM autos_db.vehicles_view v
JOIN cohort_stats c
  ON v.manufacturer = c.manufacturer
  AND v.age_bracket = c.age_bracket
  AND v.mileage_bucket = c.mileage_bucket
WHERE price > 0
  AND ABS((v.price - c.cohort_avg) / NULLIF(c.cohort_stddev, 0)) > 2
ORDER BY z_score ASC
LIMIT 50;


-- ────────────────────────────────────────────────────────────
-- QUERY 8: Duplicate Listing Detection
-- Business question: How much of the inventory is duplicate
--   or re-listed? How significantly does this inflate apparent
--   market size?
-- Use case: Data quality audit. Duplicate listings cause
--   overstated supply figures, which distort supply/demand
--   ratios and price benchmarks used by downstream KPIs.
-- Definition: Exact match on price + manufacturer + model +
--   odometer + state (same vehicle re-posted).
-- ────────────────────────────────────────────────────────────
SELECT
  price,
  manufacturer,
  model,
  odometer,
  state,
  COUNT(*) AS duplicate_count
FROM autos_db.vehicles_view
WHERE price > 0
  AND manufacturer IS NOT NULL
GROUP BY price, manufacturer, model, odometer, state
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
LIMIT 30;

-- ============================================
-- U.S. Used Vehicle Market Intelligence Queries
-- Database: autos_db | Table: vehicles
-- ============================================

-- Query 1: Price Depreciation by Manufacturer and Age Bracket
SELECT 
    manufacturer,
    age_bracket,
    ROUND(AVG(price), 2) as avg_price,
    COUNT(*) as listing_count
FROM autos_db.vehicles
WHERE manufacturer IS NOT NULL
GROUP BY manufacturer, age_bracket
ORDER BY manufacturer, age_bracket;

-- Query 2: Regional Demand Index
SELECT 
    state,
    COUNT(*) as total_listings,
    ROUND(AVG(price), 2) as avg_price,
    ROUND(AVG(vehicle_age), 1) as avg_vehicle_age,
    RANK() OVER (ORDER BY COUNT(*) DESC) as demand_rank
FROM autos_db.vehicles
GROUP BY state
ORDER BY demand_rank;

-- Query 3: Condition Premium by Manufacturer
SELECT
    manufacturer,
    condition,
    ROUND(AVG(price), 2) as avg_price,
    COUNT(*) as listing_count,
    RANK() OVER (PARTITION BY manufacturer ORDER BY AVG(price) DESC) as condition_rank
FROM autos_db.vehicles
WHERE condition IN ('excellent', 'good', 'fair', 'like new')
AND manufacturer IS NOT NULL
GROUP BY manufacturer, condition
HAVING COUNT(*) > 10
ORDER BY manufacturer, condition_rank;

-- Query 4: Mileage Discount Curve
SELECT
    manufacturer,
    mileage_bucket,
    ROUND(AVG(price), 2) as avg_price,
    COUNT(*) as listing_count
FROM autos_db.vehicles
WHERE manufacturer IS NOT NULL
GROUP BY manufacturer, mileage_bucket
HAVING COUNT(*) > 10
ORDER BY manufacturer, mileage_bucket;

-- Query 5: Deal Depth by State (avg % below market median)
SELECT
    state,
    COUNT(*) as great_deal_count,
    ROUND(AVG((state_make_median_price - price) / state_make_median_price * 100), 2) as avg_pct_below_market,
    ROUND(AVG(price), 2) as avg_deal_price,
    RANK() OVER (ORDER BY AVG((state_make_median_price - price) / state_make_median_price * 100) DESC) as discount_depth_rank
FROM autos_db.vehicles
WHERE deal_quality = 'great_deal'
AND state_make_median_price > 0
AND price > 0
GROUP BY state
HAVING COUNT(*) > 50
ORDER BY discount_depth_rank;

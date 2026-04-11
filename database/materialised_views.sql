DROP MATERIALIZED VIEW IF EXISTS mv_nsw_property_sales;
CREATE MATERIALIZED VIEW mv_nsw_property_sales AS
SELECT *
FROM vw_nsw_property_sales;

-- Pre-aggregated views for dashboard queries
-- Grain includes all 3 filter dimensions (contract_year, post_code, property_type)
-- so every chart remains filterable by the page slicers.
-- Refresh after mv_nsw_property_sales is refreshed.

DROP MATERIALIZED VIEW IF EXISTS mv_stats_agg;
CREATE MATERIALIZED VIEW mv_stats_agg AS
SELECT
    contract_year,
    post_code,
    property_type,
    COUNT(*)             AS sales_count,
    SUM(purchase_price)  AS price_sum,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY purchase_price) AS median_price
FROM mv_nsw_property_sales
GROUP BY contract_year, post_code, property_type;


DROP MATERIALIZED VIEW IF EXISTS mv_quarterly_agg;
CREATE MATERIALIZED VIEW mv_quarterly_agg AS
SELECT
    contract_year,
    EXTRACT(QUARTER FROM contract_date)::int AS contract_quarter,
    post_code,
    property_type,
    COUNT(*)             AS sales_count,
    SUM(purchase_price)  AS price_sum,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY purchase_price) AS median_price
FROM mv_nsw_property_sales
GROUP BY contract_year, EXTRACT(QUARTER FROM contract_date)::int, post_code, property_type;


DROP MATERIALIZED VIEW IF EXISTS mv_suburb_agg;
CREATE MATERIALIZED VIEW mv_suburb_agg AS
SELECT
    suburb,
    contract_year,
    post_code,
    property_type,
    COUNT(*)             AS sales_count,
    SUM(purchase_price)  AS price_sum,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY purchase_price) AS median_price
FROM mv_nsw_property_sales
GROUP BY suburb, contract_year, post_code, property_type;


DROP MATERIALIZED VIEW IF EXISTS mv_recent_sales;
CREATE MATERIALIZED VIEW mv_recent_sales AS
SELECT
    settlement_date,
    contract_date,
    full_address,
    suburb,
    post_code,
    property_type,
    purchase_price,
    percent_interest_of_sale,
    concat(area, ' ', area_type) AS area,
    COALESCE(primary_purpose, '-') AS primary_purpose,
    COALESCE(zone_code, '-') AS zone_code,
    COALESCE(nature_of_property, '-') AS nature_of_property
FROM mv_nsw_property_sales
ORDER BY settlement_date DESC NULLS LAST, contract_date DESC NULLS LAST
LIMIT 50;

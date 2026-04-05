-- Pre-aggregated views for dashboard queries
-- Grain includes all 3 filter dimensions (contract_year, post_code, property_type)
-- so every chart remains filterable by the page slicers.
-- Refresh after mv_nsw_property_sales is refreshed.

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


CREATE MATERIALIZED VIEW mv_quarterly_agg AS
SELECT
    DATE_TRUNC('quarter', contract_date) AS contract_quarter,
    contract_year,
    post_code,
    property_type,
    COUNT(*)             AS sales_count,
    SUM(purchase_price)  AS price_sum,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY purchase_price) AS median_price
FROM mv_nsw_property_sales
GROUP BY DATE_TRUNC('quarter', contract_date), contract_year, post_code, property_type;


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

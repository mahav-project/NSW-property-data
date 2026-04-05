CREATE INDEX idx_nsw_sales_main
ON mv_nsw_property_sales (post_code, contract_year, settlement_date DESC NULLS LAST)
INCLUDE (purchase_price, settlement_year);

CREATE INDEX idx_stats_agg
    ON mv_stats_agg (post_code, contract_year, property_type);

CREATE INDEX idx_quarterly_agg
    ON mv_quarterly_agg (post_code, contract_year, property_type);

CREATE INDEX idx_suburb_agg
    ON mv_suburb_agg (post_code, contract_year, property_type);

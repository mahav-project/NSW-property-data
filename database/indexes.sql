CREATE INDEX idx_nsw_sales_main
ON mv_nsw_property_sales (post_code, contract_year, settlement_date DESC NULLS LAST)
INCLUDE (purchase_price, settlement_year);
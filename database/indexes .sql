CREATE  INDEX idx_settlement_year ON mv_nsw_property_sales (EXTRACT(YEAR FROM settlement_date));
CREATE  INDEX idx_post_code ON mv_nsw_property_sales (post_code);
CREATE  INDEX idx_contract_date ON mv_nsw_property_sales (EXTRACT(YEAR FROM contract_date));
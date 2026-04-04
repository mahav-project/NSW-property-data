import streamlit as st
from db import get_connection


# Returns total count, average price, and median price for the selection
@st.cache_data(ttl=600)
def get_sales_stats(years, postcodes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(*),
            AVG(purchase_price),
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY purchase_price)
        FROM mv_nsw_property_sales
        WHERE contract_year = ANY(%s)
          AND post_code = ANY(%s)
    """, (list(years), list(postcodes)))
    return cursor.fetchone()


# Returns the 50 most recent sales for the selection
@st.cache_data(ttl=600)
def get_recent_sales(years, postcodes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            settlement_date              AS "Settlement Date",
            contract_date                AS "Contract Date",
            full_address                 AS "Address",
            concat('$', purchase_price)  AS "Price",
            percent_interest_of_sale     AS "%% Interest Sold",
            concat(area, ' ', area_type) AS "Area",
            COALESCE(primary_purpose, '-') AS "Primary Purpose"
        FROM mv_nsw_property_sales
        WHERE contract_year = ANY(%s)
          AND settlement_year = ANY(%s)
          AND post_code = ANY(%s)
        ORDER BY settlement_date DESC NULLS LAST
        LIMIT 50
    """, (list(years), list(years), list(postcodes)))
    columns = [col.name for col in cursor.description]
    rows = cursor.fetchall()
    return columns, rows

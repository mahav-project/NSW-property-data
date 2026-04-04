import streamlit as st
from db import get_connection


@st.cache_data(ttl=600)
def get_sales_stats(years, postcodes, property_types):
    """
    Returns the total number of sales, average price, and median price
    for the given years, postcodes, and property types.
    """
    query = """
        SELECT
            COUNT(*),
            AVG(purchase_price),
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY purchase_price)
        FROM mv_nsw_property_sales
        WHERE contract_year = ANY(%s)
          AND post_code = ANY(%s)
          AND property_type = ANY(%s)
    """

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, (years, postcodes, property_types))

    total_sales, average_price, median_price = cursor.fetchone()
    return total_sales, average_price, median_price


@st.cache_data(ttl=600)
def get_recent_sales(years, postcodes, property_types):
    """
    Returns the 50 most recent sales for the given years, postcodes, and property types.
    Results are ordered by settlement date, most recent first.
    """
    query = """
        SELECT
            settlement_date                AS "Settlement Date",
            contract_date                  AS "Contract Date",
            full_address                   AS "Address",
            property_type                  AS "Type",
            concat('$', purchase_price)    AS "Price",
            percent_interest_of_sale       AS "%% Interest Sold",
            concat(area, ' ', area_type)   AS "Area",
            COALESCE(primary_purpose, '-') AS "Primary Purpose"
        FROM mv_nsw_property_sales
        WHERE contract_year   = ANY(%s)
          AND settlement_year = ANY(%s)
          AND post_code       = ANY(%s)
          AND property_type   = ANY(%s)
        ORDER BY settlement_date DESC NULLS LAST
        LIMIT 50
    """

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, (years, years, postcodes, property_types))

    columns = [col.name for col in cursor.description]
    rows = cursor.fetchall()

    return columns, rows


@st.cache_data(ttl=600)
def get_suburb_stats(years, postcodes, property_types):
    """
    Returns sales count and median price grouped by suburb.
    """
    # First find the top 20 suburbs by total sales, then get the House/Unit breakdown for those suburbs
    query = """
        WITH top_suburbs AS (
            SELECT suburb
            FROM mv_nsw_property_sales
            WHERE post_code = ANY(%s)
              AND contract_year = ANY(%s)
              AND property_type = ANY(%s)
            GROUP BY suburb
            ORDER BY COUNT(*) DESC
            LIMIT 20
        )
        SELECT m.suburb, m.property_type, COUNT(*) AS sales_count,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY m.purchase_price) AS median_price
        FROM mv_nsw_property_sales m
        JOIN top_suburbs t ON m.suburb = t.suburb
        WHERE m.post_code = ANY(%s)
          AND m.contract_year = ANY(%s)
          AND m.property_type = ANY(%s)
        GROUP BY m.suburb, m.property_type
    """

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, (postcodes, years, property_types, postcodes, years, property_types))

    columns = [col.name for col in cursor.description]
    rows = cursor.fetchall()

    return columns, rows
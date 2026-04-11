import streamlit as st
from db import get_connection


@st.cache_data(ttl=600)
def get_sales_stats(years, postcodes, property_types):
    query = """
        SELECT
            SUM(sales_count),
            SUM(price_sum) / NULLIF(SUM(sales_count), 0),
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY median_price)
        FROM mv_stats_agg
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
def get_suburb_stats(years, postcodes, property_types):
    query = """
        WITH top_suburbs AS (
            SELECT suburb
            FROM mv_suburb_agg
            WHERE post_code = ANY(%s)
              AND contract_year = ANY(%s)
              AND property_type = ANY(%s)
            GROUP BY suburb
            ORDER BY SUM(sales_count) DESC
            LIMIT 10
        )
        SELECT m.suburb, m.property_type,
               SUM(m.sales_count) AS sales_count,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY m.median_price) AS median_price
        FROM mv_suburb_agg m
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


@st.cache_data(ttl=600)
def get_price_trends(years, postcodes, property_types):
    query = """
        SELECT
            contract_year,
            contract_quarter,
            property_type,
            SUM(sales_count)                                          AS sales_count,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY median_price) AS median_price
        FROM mv_quarterly_agg
        WHERE post_code     = ANY(%s)
          AND contract_year = ANY(%s)
          AND property_type = ANY(%s)
        GROUP BY contract_year, contract_quarter, property_type
        ORDER BY contract_year, contract_quarter
    """

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, (postcodes, years, property_types))

    columns = [col.name for col in cursor.description]
    rows = cursor.fetchall()

    return columns, rows

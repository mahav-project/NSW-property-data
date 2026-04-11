import streamlit as st
from db import get_connection

st.set_page_config(page_title="NSW Property Sales", layout="wide")

st.markdown("<h1 style='text-align:center'>🏡 NSW Property Sales Dashboard</h1>", unsafe_allow_html=True)

st.markdown("""
Explore residential property sales data across New South Wales, sourced from the
[NSW Valuer General](https://valuation.property.nsw.gov.au/embed/propertySalesInformation).

**What's included:**
- Sales records for houses and units across NSW postcodes
- Price trends, suburb breakdowns, and recent transactions

Use the sidebar to navigate between pages.

**Coming soon:**
- Suburb comparison tool
- Year-on-year growth analysis
- Downloadable reports
- Interactive map view
""")


@st.cache_data(ttl=600)
def get_recent_sales():
    query = """
        SELECT
            settlement_date    AS "Settlement Date",
            contract_date      AS "Contract Date",
            full_address       AS "Address",
            suburb             AS "Suburb",
            post_code          AS "Postcode",
            property_type      AS "Type",
            concat('$', purchase_price) AS "Price",
            percent_interest_of_sale    AS "% Interest Sold",
            area               AS "Area",
            primary_purpose    AS "Primary Purpose",
            zone_code          AS "Zone",
            nature_of_property AS "Nature of Property"
        FROM mv_recent_sales
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    columns = [col.name for col in cursor.description]
    rows = cursor.fetchall()
    return columns, rows


st.subheader("Recent Sales — Sample Data")

try:
    columns, rows = get_recent_sales()
    table_data = [dict(zip(columns, row)) for row in rows]
    st.dataframe(table_data, use_container_width=True, hide_index=True)
except Exception as error:
    st.error("Database error: " + str(error))

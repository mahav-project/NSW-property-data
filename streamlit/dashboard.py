import streamlit as st
import psycopg2

st.set_page_config(page_title="NSW Property Sales", layout="wide")


# Connect to the RDS database using credentials from .streamlit/secrets.toml
@st.cache_resource
def get_connection():
    db = st.secrets["database"]
    conn = psycopg2.connect(
        host=db["host"],
        port=db["port"],
        dbname=db["dbname"],
        user=db["user"],
        password=db["password"]
    )
    return conn


# Build the year and postcode options for the filters
years = []
for y in range(2026, 1989, -1):
    years.append(y)

postcodes = []
for p in range(2000, 3001):
    postcodes.append(str(p))


st.title("NSW Property Sales Dashboard")

col1, col2 = st.columns(2)

selected_years = col1.multiselect(
    "Years",
    options=years,
    default=[],
    placeholder="All Years"
)

selected_postcodes = col2.multiselect(
    "Postcodes",
    options=postcodes,
    default=[],
    placeholder="All Postcodes"
)

# If nothing is selected, query everything
years_to_query = selected_years if selected_years else years
postcodes_to_query = selected_postcodes if selected_postcodes else postcodes


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
        FROM vw_nsw_property_sales
        WHERE EXTRACT(YEAR FROM contract_date) = ANY(%s)
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
            settlement_date      AS "Settlement Date",
            contract_date        AS "Contract Date",
            full_address         AS "Address",
            concat('$', purchase_price) AS "Price",
            percent_interest_of_sale    AS "%% Interest Sold",
            concat(area, ' ', area_type) AS "Area",
            COALESCE(primary_purpose, '-') AS "Primary Purpose"
        FROM vw_nsw_property_sales
        WHERE EXTRACT(YEAR FROM contract_date) = ANY(%s)
          AND (EXTRACT(YEAR FROM settlement_date) = ANY(%s) OR settlement_date IS NULL)
          AND post_code = ANY(%s)
        ORDER BY settlement_date DESC NULLS LAST
        LIMIT 50
    """, (list(years), list(years), list(postcodes)))
    columns = [col.name for col in cursor.description]
    rows = cursor.fetchall()
    return columns, rows


try:
    count, avg_price, median_price = get_sales_stats(years_to_query, postcodes_to_query)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sales",   f"{count:,}")
    col2.metric("Average Price", f"${avg_price:,.0f}"    if avg_price    else "N/A")
    col3.metric("Median Price",  f"${median_price:,.0f}" if median_price else "N/A")

    st.subheader("Recent Sales")
    columns, rows = get_recent_sales(years_to_query, postcodes_to_query)

    # Turn rows into a list of dicts so st.dataframe can label the columns
    table_data = []
    for row in rows:
        table_data.append(dict(zip(columns, row)))

    st.dataframe(table_data, use_container_width=True, hide_index=True)

except Exception as error:
    st.error("Database error: " + str(error))
    st.stop()

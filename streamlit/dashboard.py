import streamlit as st
from queries import get_sales_stats, get_recent_sales

st.set_page_config(page_title="NSW Property Sales", layout="wide")

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


try:
    count, avg_price, median_price = get_sales_stats(years_to_query, postcodes_to_query)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sales",   f"{count:,}")
    col2.metric("Average Price", f"${avg_price:,.0f}"    if avg_price    else "N/A")
    col3.metric("Median Price",  f"${median_price:,.0f}" if median_price else "N/A")

    st.subheader("Recent Sales")
    columns, rows = get_recent_sales(years_to_query, postcodes_to_query)

    table_data = []
    for row in rows:
        table_data.append(dict(zip(columns, row)))

    st.dataframe(table_data, use_container_width=True, hide_index=True)

except Exception as error:
    st.error("Database error: " + str(error))
    st.stop()

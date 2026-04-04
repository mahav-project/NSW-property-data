import streamlit as st
import plotly.express as px
from queries import get_sales_stats, get_recent_sales, get_suburb_stats
from concurrent.futures import ThreadPoolExecutor
import time

st.set_page_config(page_title="NSW Property Sales", layout="wide")

# Build the year and postcode options for the filters
years = []
for y in range(2026, 1989, -1):
    years.append(y)

postcodes = []
for p in range(2000, 3001):
    postcodes.append(str(p))


st.markdown("<h1 style='text-align:center'>🏡 NSW Property Sales Dashboard</h1>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

selected_years = col1.multiselect(
    "Years",
    options=years,
    default=[2025],
    placeholder="All Years"
)

selected_postcodes = col2.multiselect(
    "Postcodes",
    options=postcodes,
    default=[],
    placeholder="All Postcodes"
)

selected_property_type = col3.multiselect(
    "Property Type",
    options=["House", "Unit"],
    default=[],
    placeholder="All Property Types"
)

# If nothing is selected, query everything
years_to_query = selected_years if selected_years else years
postcodes_to_query = selected_postcodes if selected_postcodes else postcodes
property_type_to_query = selected_property_type if selected_property_type else ["House", "Unit"]


def get_all_data(years, postcodes, property_types):
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_stats  = executor.submit(get_sales_stats,   years, postcodes, property_types)
        f_sales  = executor.submit(get_recent_sales,  years, postcodes, property_types)
        f_suburb = executor.submit(get_suburb_stats,  years, postcodes, property_types)
    return f_stats.result(), f_sales.result(), f_suburb.result()

try:
    with st.spinner("Loading data..."):
        start = time.perf_counter()
        f_stats, f_sales, f_suburb = get_all_data(years_to_query, postcodes_to_query, property_type_to_query)
        elapsed_ms = (time.perf_counter() - start) * 1000
        st.caption(f"⚡ Loaded in {elapsed_ms:.0f}ms")
        st.subheader("Overall Stats")
        count, avg_price, median_price = f_stats

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Sales",   f"{count:,}")
        col2.metric("Average Price", f"${avg_price:,.0f}"    if avg_price    else "N/A")
        col3.metric("Median Price",  f"${median_price:,.0f}" if median_price else "N/A")

        st.subheader("Sales by Suburb")
        columns, rows = f_suburb
        suburb_data = [dict(zip(columns, row)) for row in rows]
        fig = px.bar(
            suburb_data,
            x="sales_count", y="suburb", orientation="h",
            labels={"sales_count": "Sales", "suburb": "Suburb"},
            text="sales_count"
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Recent Sales")
        columns, rows = f_sales

        table_data = []
        for row in rows:
            table_data.append(dict(zip(columns, row)))

        st.dataframe(table_data, use_container_width=True, hide_index=True)

except Exception as error:
    st.error("Database error: " + str(error))
    st.stop()

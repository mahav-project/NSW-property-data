import streamlit as st
import plotly.express as px
from queries import get_sales_stats, get_recent_sales, get_suburb_stats, get_price_trends
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
    default=[],
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
        f_suburb = executor.submit(get_suburb_stats,  years, postcodes, property_types)
        f_trends = executor.submit(get_price_trends,  years, postcodes, property_types)
    return f_stats.result(),  f_suburb.result(), f_trends.result()

try:
    with st.spinner("Loading data..."):
        start = time.perf_counter()
        f_stats, f_suburb, f_trends = get_all_data(years_to_query, postcodes_to_query, property_type_to_query)
        elapsed_ms = (time.perf_counter() - start) * 1000
        st.caption(f"⚡ Loaded in {elapsed_ms:.0f}ms")
        # Overall Stats
        with st.container():
            st.subheader("Overall Stats")
            count, avg_price, median_price = f_stats

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Sales",   f"{count:,}")
            col2.metric("Average Price", f"${avg_price:,.0f}"    if avg_price    else "N/A")
            col3.metric("Median Price",  f"${median_price:,.0f}" if median_price else "N/A")

        # Quarterly Trends (side by side)
        with st.container():
            columns, rows = f_trends
            trend_data = [dict(zip(columns, row)) for row in rows]
            for row in trend_data:
                dt = row["contract_quarter"]
                row["contract_quarter"] = f"Q{(dt.month - 1) // 3 + 1} {dt.year}"

            col_vol, col_price = st.columns(2)

            with col_vol:
                st.subheader("Sale Volume by Quarter")
                fig_vol = px.bar(
                    trend_data,
                    x="contract_quarter",
                    y="sales_count",
                    color="property_type",
                    barmode="stack",
                    labels={
                        "contract_quarter": "Quarter",
                        "sales_count":      "Sales",
                        "property_type":    "Type",
                    },
                    text="sales_count",
                )
                fig_vol.update_traces(
                    textposition="inside",
                    textfont={"size": 13, "color": "white"},
                    insidetextanchor="middle",
                )
                fig_vol.update_layout(height=400)
                st.plotly_chart(fig_vol, use_container_width=True)

            with col_price:
                st.subheader("Median Price by Quarter")
                fig_price = px.line(
                    trend_data,
                    x="contract_quarter",
                    y="median_price",
                    color="property_type",
                    markers=True,
                    labels={
                        "contract_quarter": "Quarter",
                        "median_price":     "Median Price ($)",
                        "property_type":    "Type",
                    },
                )
                fig_price.update_layout(
                    yaxis={"tickprefix": "$", "tickformat": ",.0f"},
                    height=400,
                )
                st.plotly_chart(fig_price, use_container_width=True)

        # Sales by Suburb
        with st.container():
            st.subheader("Sales by Suburb (Top 10)")

            columns, rows = f_suburb
            suburb_data = [dict(zip(columns, row)) for row in rows]

            fig = px.bar(
                suburb_data,
                x="sales_count",
                y="suburb",
                orientation="h",
                color="property_type",
                barmode="stack",
                labels={
                    "sales_count":    "Sales",
                    "suburb":         "Suburb",
                    "property_type":  "Type",
                },
                text="sales_count",
            )
            fig.update_traces(
                textposition="inside",
                textfont={"size": 13, "color": "white"},  # or "black" depending on bar color
                insidetextanchor="middle",
            )
            fig.update_layout(
                yaxis={"categoryorder": "total ascending"},
                height=max(500, len(suburb_data) * 30),  # ~40px per bar
            )
            st.plotly_chart(fig, use_container_width=True)

        #Recent Sales
        with st.container():
            st.subheader("Recent 50 Sales")
            f_sales = get_recent_sales(years_to_query, postcodes_to_query, property_type_to_query)

            columns, rows = f_sales
            table_data = [dict(zip(columns, row)) for row in rows]

            st.dataframe(table_data, use_container_width=True, hide_index=True)

except Exception as error:
    st.error("Database error: " + str(error))
    st.stop()

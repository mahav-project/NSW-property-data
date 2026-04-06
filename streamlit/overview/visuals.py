import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor
import time

from overview.queries import get_sales_stats, get_recent_sales, get_suburb_stats, get_price_trends


def _load_data(years, postcodes, property_types):
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_stats  = executor.submit(get_sales_stats,  years, postcodes, property_types)
        f_suburb = executor.submit(get_suburb_stats, years, postcodes, property_types)
        f_trends = executor.submit(get_price_trends, years, postcodes, property_types)
    return f_stats.result(), f_suburb.result(), f_trends.result()


def render(years, postcodes, property_types):
    try:
        with st.spinner("Loading data..."):
            start = time.perf_counter()
            f_stats, f_suburb, f_trends = _load_data(years, postcodes, property_types)
            elapsed_ms = (time.perf_counter() - start) * 1000
            st.caption(f"⚡ Loaded in {elapsed_ms:.0f}ms")

            # Overall Stats
            st.subheader("Overall Stats")
            count, avg_price, median_price = f_stats

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Sales",   f"{count:,}")
            col2.metric("Average Price", f"${avg_price:,.0f}"    if avg_price    else "N/A")
            col3.metric("Median Price",  f"${median_price:,.0f}" if median_price else "N/A")

            # Quarterly Trends
            columns, rows = f_trends
            trend_data = [dict(zip(columns, row)) for row in rows]
            for row in trend_data:
                row["contract_quarter"] = f"Q{row['contract_quarter']} {row['contract_year']}"

            year_labels = sorted({row["contract_year"] for row in trend_data})
            col_vol, col_price = st.columns(2)

            with col_vol:
                st.subheader("Sale Volume by Quarter")
                fig_vol = px.bar(
                    trend_data,
                    x="contract_quarter",
                    y="sales_count",
                    color="property_type",
                    barmode="stack",
                    color_discrete_map={"House": "#636EFA", "Unit": "#EF553B"},
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
                fig_vol.update_layout(
                    height=400,
                    xaxis={
                        "tickvals": [f"Q1 {y}" for y in year_labels],
                        "ticktext": [str(y) for y in year_labels],
                    },
                )
                st.plotly_chart(fig_vol, use_container_width=True)

            with col_price:
                st.subheader("Median Price by Quarter")
                fig_price = px.line(
                    trend_data,
                    x="contract_quarter",
                    y="median_price",
                    color="property_type",
                    markers=True,
                    color_discrete_map={"House": "#636EFA", "Unit": "#EF553B"},
                    labels={
                        "contract_quarter": "Quarter",
                        "median_price":     "Median Price ($)",
                        "property_type":    "Type",
                    },
                )
                fig_price.update_layout(
                    yaxis={"tickprefix": "$", "tickformat": ",.0f"},
                    xaxis={
                        "tickvals": [f"Q1 {y}" for y in year_labels],
                        "ticktext": [str(y) for y in year_labels],
                    },
                    height=400,
                )
                st.plotly_chart(fig_price, use_container_width=True)

            # Sales by Suburb
            st.subheader("Top 10 Suburbs")

            columns, rows = f_suburb
            suburb_data = [dict(zip(columns, row)) for row in rows]

            suburbs = sorted(
                {r["suburb"] for r in suburb_data},
                key=lambda s: sum(r["sales_count"] for r in suburb_data if r["suburb"] == s),
                reverse=True,
            )
            colors = {"House": "#636EFA", "Unit": "#EF553B"}

            col_sub_vol, col_sub_price = st.columns(2)

            with col_sub_vol:
                st.subheader("Sales by Suburb")
                fig_sub_vol = go.Figure()
                for ptype in ["House", "Unit"]:
                    subset = {r["suburb"]: r for r in suburb_data if r["property_type"] == ptype}
                    fig_sub_vol.add_trace(go.Bar(
                        x=suburbs,
                        y=[subset[s]["sales_count"] if s in subset else 0 for s in suburbs],
                        name=ptype,
                        marker_color=colors[ptype],
                    ))
                fig_sub_vol.update_layout(barmode="group", yaxis={"title": "Sales"}, height=400)
                st.plotly_chart(fig_sub_vol, use_container_width=True)

            with col_sub_price:
                st.subheader("Median Price by Suburb")
                fig_sub_price = go.Figure()
                for ptype in ["House", "Unit"]:
                    subset = {r["suburb"]: r for r in suburb_data if r["property_type"] == ptype}
                    fig_sub_price.add_trace(go.Bar(
                        x=suburbs,
                        y=[subset[s]["median_price"] if s in subset else 0 for s in suburbs],
                        name=ptype,
                        marker_color=colors[ptype],
                    ))
                fig_sub_price.update_layout(
                    barmode="group",
                    yaxis={"title": "Median Price ($)", "tickprefix": "$", "tickformat": ",.0f"},
                    height=400,
                )
                st.plotly_chart(fig_sub_price, use_container_width=True)

        # Recent Sales
        st.subheader("Recent 50 Sales")
        f_sales = get_recent_sales(years, postcodes, property_types)
        columns, rows = f_sales
        table_data = [dict(zip(columns, row)) for row in rows]
        st.dataframe(table_data, use_container_width=True, hide_index=True)

    except Exception as error:
        st.error("Database error: " + str(error))
        st.stop()

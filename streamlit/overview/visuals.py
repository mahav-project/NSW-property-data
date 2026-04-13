import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor
import time

from overview.queries import get_sales_stats, get_suburb_stats, get_price_trends
from plotly.subplots import make_subplots


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
            fig_suburb = make_subplots(specs=[[{"secondary_y": True}]])

            for ptype, color in [("House", "#636EFA"), ("Unit", "#FF7F50")]:
                subset = {r["suburb"]: r for r in suburb_data if r["property_type"] == ptype}
                fig_suburb.add_trace(
                    go.Bar(
                        x=suburbs,
                        y=[subset[s]["sales_count"] if s in subset else 0 for s in suburbs],
                        name=f"{ptype} sales",
                        marker_color=color,
                    ),
                    secondary_y=False,
                )

            PRICE_CAP = 3_000_000

            for ptype, dash, color in [("House", "solid", "#1B3A6B"), ("Unit", "dash", "#E8590C")]:
                subset = {r["suburb"]: r for r in suburb_data if r["property_type"] == ptype}
                real_prices = [float(subset[s]["median_price"]) if s in subset else 0 for s in suburbs]
                capped_prices = [min(p, PRICE_CAP) for p in real_prices]
                capped_mask = [p > PRICE_CAP for p in real_prices]

                # Main line with regular markers
                fig_suburb.add_trace(
                    go.Scatter(
                        x=suburbs,
                        y=capped_prices,
                        name=f"{ptype} price",
                        mode="lines+markers",
                        line={"dash": dash, "color": color, "width": 2.5},
                        marker={"size": 8},
                        customdata=real_prices,
                        hovertemplate="%{x}<br>Median: $%{customdata:,.0f}<extra></extra>",
                    ),
                    secondary_y=True,
                )

                # Overlay amber triangles on capped points
                if any(capped_mask):
                    fig_suburb.add_trace(
                        go.Scatter(
                            x=[s for s, m in zip(suburbs, capped_mask) if m],
                            y=[PRICE_CAP for m in capped_mask if m],
                            mode="markers",
                            marker={"symbol": "triangle-up", "size": 14, "color": "#FFB020",
                                    "line": {"width": 1.5, "color": "#CC8800"}},
                            customdata=[p for p, m in zip(real_prices, capped_mask) if m],
                            hovertemplate="%{x}<br>Median: $%{customdata:,.0f} (capped at $3M)<extra></extra>",
                            showlegend=False,
                        ),
                        secondary_y=True,
                    )

            fig_suburb.update_layout(
                barmode="group",
                height=450,
                legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "center", "x": 0.5},
            )
            fig_suburb.update_yaxes(title_text="Sales Volume", ticksuffix="k", tickformat=".0f",
                                    dtick=10000, secondary_y=False)
            price_ticks = list(range(0, PRICE_CAP + 1, 200_000))
            price_labels = []
            for v in price_ticks:
                if v == 0:
                    price_labels.append("$0")
                elif v < 1_000_000:
                    price_labels.append(f"${v // 1000}k")
                elif v % 1_000_000 == 0:
                    price_labels.append(f"${v // 1_000_000}M")
                else:
                    price_labels.append(f"${v / 1_000_000:.1f}M")
            fig_suburb.update_yaxes(title_text="Median Price ($M)",
                                    range=[0, PRICE_CAP * 1.05],
                                    tickvals=price_ticks, ticktext=price_labels,
                                    secondary_y=True)

            st.plotly_chart(fig_suburb, use_container_width=True)

    except Exception as error:
        st.error("Database error: " + str(error))
        st.stop()

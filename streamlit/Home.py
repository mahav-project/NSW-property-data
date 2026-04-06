import streamlit as st

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

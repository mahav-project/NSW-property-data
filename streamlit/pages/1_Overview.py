import streamlit as st
from filters import render_filters
from overview.visuals import render

st.set_page_config(page_title="Overview — NSW Property Sales", layout="wide")

st.markdown("<h1 style='text-align:center'>🏡 Overview</h1>", unsafe_allow_html=True)

years, postcodes, property_types = render_filters()
render(years, postcodes, property_types)

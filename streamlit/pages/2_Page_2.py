import streamlit as st
from filters import render_filters
from page_2.visuals import render

st.set_page_config(page_title="Page 2 — NSW Property Sales", layout="wide")

st.markdown("<h1 style='text-align:center'>📊 Page 2</h1>", unsafe_allow_html=True)

years, postcodes, property_types = render_filters()
render(years, postcodes, property_types)

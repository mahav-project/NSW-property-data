import streamlit as st

YEARS = list(range(2026, 1989, -1))
POSTCODES = [str(p) for p in range(2000, 3001)]
PROPERTY_TYPES = ["House", "Unit"]


def render_filters():
    st.sidebar.header("Filters")

    selected_years = st.sidebar.multiselect(
        "Years", options=YEARS, default=[], placeholder="All Years"
    )
    selected_postcodes = st.sidebar.multiselect(
        "Postcodes", options=POSTCODES, default=[], placeholder="All Postcodes"
    )
    selected_property_type = st.sidebar.multiselect(
        "Property Type", options=PROPERTY_TYPES, default=[], placeholder="All Property Types"
    )

    years = selected_years if selected_years else YEARS
    postcodes = selected_postcodes if selected_postcodes else POSTCODES
    property_types = selected_property_type if selected_property_type else PROPERTY_TYPES

    return years, postcodes, property_types

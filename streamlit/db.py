import streamlit as st
import psycopg2


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
    conn.autocommit = True
    return conn

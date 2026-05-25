"""Outreach CRM — Streamlit entry point.

This is the Walking Skeleton: sets page config, initializes session state,
bootstraps the database, and renders sidebar branding.

Page routing is handled automatically by Streamlit's multipage mechanism
via the pages/ directory — no explicit routing code here.
"""
import streamlit as st

# FIRST: set_page_config must be the very first Streamlit call in the entry point.
st.set_page_config(
    page_title="Outreach CRM",
    page_icon=":outbox_tray:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# SECOND: initialize session state before any data access
from utils.session import init_session_state

init_session_state()

# THIRD: bootstrap the database (idempotent — IF NOT EXISTS guards in schema)
from database.schema import init_db

init_db()

# Sidebar branding
st.sidebar.title("Outreach CRM")
st.sidebar.caption("AI/ML Startup Outreach")

# Main page content
st.title("Outreach CRM")
st.write("Welcome. Use the sidebar to navigate.")

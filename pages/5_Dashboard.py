import streamlit as st
from utils.session import init_session_state

st.set_page_config(
    page_title="Outreach CRM",
    page_icon=":outbox_tray:",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

st.title("Dashboard")
st.info("Coming soon — built in Phase 4.")

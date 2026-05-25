"""My Profile page — Phase 1 shell.

Full implementation in Phase 1, Plan 03 (FOUND-03).
This shell renders the page title and an informational banner
if the profile has not been filled in yet. Form functionality
is added in Plan 03.
"""
import streamlit as st
from utils.session import init_session_state

init_session_state()

st.title("My Profile")
st.info("Coming soon — built in Phase 2/3/4.")

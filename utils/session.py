"""Session state initialization for Outreach CRM.

Every page must call init_session_state() as its second call (after set_page_config)
to prevent KeyError when Streamlit renders a page cold (user navigates directly by URL).
"""
import streamlit as st

SESSION_DEFAULTS: dict = {
    "profile_loaded": False,
    "profile": {},
    "selected_company_id": None,
    "selected_contact_id": None,
    "discover_results": [],
    "discover_running": False,
    "draft_email_text": "",
    "draft_contact_id": None,
    "tracker_filter_status": "All",
    "dashboard_filter": {},
}


def init_session_state() -> None:
    """Initialize session state keys with defaults if not already set.

    Idempotent — only sets keys that are not already in st.session_state.
    """
    for key, default in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default

"""Discover page — Phase 2: AI/ML startup discovery via Claude web_search.

Allows users to set filters (location, tier, role type), trigger a Claude-powered
company search, view results as a 3-column card grid, and save companies one-click.
"""
import html

import streamlit as st

from database.companies import get_saved_company_identifiers, save_company
from services.claude import discover_companies
from utils.session import init_session_state

st.set_page_config(
    page_title="Outreach CRM",
    page_icon=":outbox_tray:",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAVED_BADGE_HTML = (
    '<span style="background-color:#16a34a;color:#ffffff;'
    'padding:4px 8px;border-radius:4px;font-size:13px;font-weight:600;">'
    'Saved &#10003;</span>'
)


# ---------------------------------------------------------------------------
# Card renderer
# ---------------------------------------------------------------------------


def render_company_card(
    company,
    saved_names: set,
    saved_urls: set,
    card_index: int,
) -> None:
    """Render a single company card inside the caller's column context.

    Args:
        company: Company pydantic model instance from services/claude.py.
        saved_names: Set of lowercase company names already in DB (from batch query).
        saved_urls: Set of normalized URLs already in DB (from batch query).
        card_index: Position in the results list — used for unique Save button keys.
    """
    with st.container():
        st.write(f"**{html.escape(company.name)}**")
        st.write(f"Stage: {company.funding_stage}  |  Headcount: {company.headcount}")
        st.write(f"Focus: {html.escape(company.ai_focus or '')}")
        if company.website:
            st.write(f"[{company.website}]({company.website})")
        if company.hiring_roles:
            st.caption(
                f"Roles: {', '.join(html.escape(r) for r in company.hiring_roles)}"
            )

        # Duplicate detection (D-08): name match OR url match is a hit.
        is_saved = (company.name.lower() in saved_names) or (
            company.website is not None
            and company.website.rstrip("/").lower() in saved_urls
        )

        if is_saved:
            st.markdown(SAVED_BADGE_HTML, unsafe_allow_html=True)
        else:
            if st.button("Save", key=f"save_{card_index}_{company.name}"):
                save_company(company)
                st.success(f"{company.name} saved.")
                st.rerun()

    st.write("")  # breathing room between cards in the same column


# ---------------------------------------------------------------------------
# Page title — Section D
# ---------------------------------------------------------------------------

st.title("Discover")
st.caption(
    "Find AI/ML startups matching your target. "
    "Claude searches the web and returns live results."
)
st.divider()

# ---------------------------------------------------------------------------
# Filter widgets — Section E
# ---------------------------------------------------------------------------

col1, col2 = st.columns(2)
with col1:
    location = st.selectbox(
        "Location",
        options=["NYC", "Arlington VA", "DC", "SF"],
        index=0,
        key="discover_location",
    )
with col2:
    tier = st.selectbox(
        "Tier",
        options=["Tier 2", "Tier 3", "Both"],
        index=2,
        key="discover_tier",
    )

role_type = st.selectbox(
    "Role Type",
    options=["Internship", "Full-time", "Both"],
    index=2,
    key="discover_role_type",
)

# ---------------------------------------------------------------------------
# Discover button — Section F
# ---------------------------------------------------------------------------

discover_clicked = st.button(
    "Discover",
    type="primary",
    disabled=st.session_state["discover_running"],
    use_container_width=False,
)

# ---------------------------------------------------------------------------
# Discover click handler — Section G (D-02, D-04, blocking call with spinner)
# ---------------------------------------------------------------------------

if discover_clicked:
    filters = {"location": location, "tier": tier, "role_type": role_type}
    st.session_state["discover_running"] = True
    try:
        with st.spinner("Claude is searching..."):
            results = discover_companies(filters)
        st.session_state["discover_results"] = results
    except Exception as e:
        st.error(f"Search failed: {e}")
    finally:
        st.session_state["discover_running"] = False
    st.rerun()

# ---------------------------------------------------------------------------
# Empty state — Section H (D-07: no results, not mid-search)
# ---------------------------------------------------------------------------

if (
    not st.session_state["discover_results"]
    and not st.session_state["discover_running"]
):
    st.info(
        "Set your filters above and click **Discover** to find AI/ML startups. "
        "Claude will search the web and return live results."
    )

# ---------------------------------------------------------------------------
# Results grid — Section I (D-05 persist, D-09 batch check, D-10 badge)
# ---------------------------------------------------------------------------

results = st.session_state["discover_results"]
if results:
    if len(results) == 0:
        st.warning(
            "No matching companies found. "
            "Try adjusting your filters or broadening the tier."
        )
    else:
        st.subheader(f"Results ({len(results)})")
        st.caption("Click Save to add a company to your pipeline.")
        st.divider()

        # Batch duplicate check once — not per card (D-09).
        saved_names, saved_urls = get_saved_company_identifiers()

        cols = st.columns(3)
        for i, company in enumerate(results):
            with cols[i % 3]:
                render_company_card(company, saved_names, saved_urls, i)

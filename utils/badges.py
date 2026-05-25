"""Status badge utility for Outreach CRM.

Defines STATUS_COLORS and status_badge() for use in Phase 4 tracker page.
No Streamlit import — pure Python utility.

Callers must validate that status is a known key before passing to status_badge()
to prevent XSS via unsafe_allow_html=True in st.markdown (see threat T-03-01).
"""

STATUS_COLORS: dict[str, dict[str, str]] = {
    "Not Contacted": {"bg": "#e5e7eb", "text": "#374151"},
    "Drafted":       {"bg": "#fef3c7", "text": "#92400e"},
    "Sent":          {"bg": "#dbeafe", "text": "#1e40af"},
    "Replied":       {"bg": "#d1fae5", "text": "#065f46"},
    "Interview":     {"bg": "#16a34a", "text": "#ffffff"},
    "Rejected":      {"bg": "#fee2e2", "text": "#991b1b"},
}


def status_badge(status: str) -> str:
    """Return an HTML span styled as a status badge.

    Args:
        status: One of the known STATUS_COLORS keys. Unknown values fall back
                to the 'Not Contacted' color scheme.

    Returns:
        An HTML string safe to pass to st.markdown(..., unsafe_allow_html=True).
        Only call with a validated status from STATUS_COLORS.keys().
    """
    c = STATUS_COLORS.get(status, {"bg": "#e5e7eb", "text": "#374151"})
    return (
        f'<span style="background-color:{c["bg"]};color:{c["text"]};'
        f'padding:2px 8px;border-radius:4px;font-size:13px;font-weight:600;">'
        f'{status}</span>'
    )

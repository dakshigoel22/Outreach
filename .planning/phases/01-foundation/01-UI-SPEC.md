---
status: draft
phase: 1
phase_name: Foundation
created: 2026-05-24
author: gsd-ui-researcher
---

# UI-SPEC: Phase 1 — Foundation

## Design System

**Tool:** None (no shadcn — Python/Streamlit project).  
**Styling mechanism:** Streamlit native theming via `.streamlit/config.toml` + inline
`st.markdown` for badge colors only. No custom CSS framework. No external component
libraries in Phase 1.

---

## Color Palette

| Role | Hex | Where Used |
|------|-----|-----------|
| Primary | `#3b82f6` | Buttons, active nav highlight, links, form Save button |
| Background | `#ffffff` | Main page canvas |
| Secondary Background | `#f0f2f6` | Sidebar, info boxes, card-like containers |
| Text | `#1a1a2e` | All body copy, labels, table content |
| Success | `#16a34a` | `st.success`, "Saved" feedback, Interview status badge |
| Error / Destructive | `#dc2626` | `st.error`, Rejected status badge, validation errors |
| Warning | `#d97706` | `st.warning`, stale-state notices |
| Info | `#3b82f6` | `st.info`, coming-soon banners (same as primary) |

**60 / 30 / 10 split:**
- 60% white `#ffffff` — page background, form fields
- 30% light gray `#f0f2f6` — sidebar, section dividers, secondary containers
- 10% blue `#3b82f6` — all interactive affordances (buttons, active state, links)

Accent (`#3b82f6`) is reserved exclusively for: primary action buttons, the currently
active sidebar nav item, hyperlinks, and spinner stroke color. It is NOT used for
decorative borders or section headers.

---

## Streamlit config.toml

File path: `.streamlit/config.toml`

```toml
[theme]
primaryColor        = "#3b82f6"
backgroundColor     = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor           = "#1a1a2e"
font                = "sans serif"

[server]
headless = true
port = 8501

[browser]
gatherUsageStats = false
```

`font = "sans serif"` uses Streamlit's built-in Inter/system sans-serif stack. Do NOT
set a Google Fonts import — it adds a network request and requires a custom CSS block.

---

## Page Layout

| Setting | Value | Rationale |
|---------|-------|-----------|
| `st.set_page_config(layout=...)` | `"wide"` | Data-dense CRM; tables need horizontal space |
| Sidebar | Always visible (Streamlit default) | Nav must be accessible on every page without expanding |
| Page icon | `":outbox_tray:"` | Maps to outreach theme; no custom image needed in Phase 1 |
| App title in browser tab | `"Outreach CRM"` | Set via `page_title="Outreach CRM"` in `set_page_config` |

Every page file must call `st.set_page_config` as its **first Streamlit call**:

```python
st.set_page_config(
    page_title="Outreach CRM",
    page_icon=":outbox_tray:",
    layout="wide",
    initial_sidebar_state="expanded",
)
```

---

## Navigation Structure

**Multi-page via `pages/` directory.** Streamlit reads file names for sidebar order.
Use numeric prefix to enforce order. Underscores become spaces in the sidebar label.

```
app.py                         # Entry point — runs set_page_config, session state init, redirects to My Profile
pages/
  1_Discover.py
  2_Contacts.py
  3_Draft_Email.py
  4_Tracker.py
  5_Dashboard.py
  6_My_Profile.py
```

### Sidebar conventions

- App title rendered at the top of the sidebar via `st.sidebar.title("Outreach CRM")`.
- No custom nav widget — use Streamlit's built-in page list (auto-generated from `pages/`).
- Sidebar subtitle: `st.sidebar.caption("AI/ML Startup Outreach")` below the title.
- No sidebar search, filters, or widgets in Phase 1. Sidebar is nav-only.

### Phase 1 shell pages (pages 1–5)

Pages 1–5 are non-functional shells in Phase 1. Each shell renders exactly this pattern:

```python
st.title("<Page Name>")
st.info("Coming soon — built in Phase 2/3/4.")
```

No additional content, no placeholders, no fake data. The `st.info` banner uses
Streamlit's default info styling (blue, left-aligned).

---

## Typography

Streamlit does not expose direct font-size control via config. Typography is achieved
through Streamlit heading hierarchy and markdown. Do NOT use `st.markdown` with inline
`<style>` tags to override font sizes — it breaks across Streamlit version updates.

| Element | Streamlit Call | Effective Size (approx) | Weight |
|---------|---------------|------------------------|--------|
| Page title | `st.title()` | ~28px | Bold (700) |
| Section header | `st.header()` | ~20px | Semibold (600) |
| Subsection | `st.subheader()` | ~16px | Semibold (600) |
| Body / labels | `st.write()`, `st.caption()` | ~14–16px | Regular (400) |

**Two weights only:** Regular (400) for body/labels, Bold/Semibold (600–700) for
headings. No italics except `st.caption()` for helper text below form fields.

**Line height:** Streamlit default (approx 1.5 for body, 1.2 for headings). Do not
override.

---

## Component Patterns — My Profile Page (FOUND-03)

### Form layout

Use `st.form(key="my_profile_form")` to batch all field writes into one DB call on
submit. Do NOT use individual `st.text_input` with `on_change` callbacks — they fire
on every keystroke and create excessive DB writes.

```python
with st.form(key="my_profile_form"):
    # --- Two-column row for short fields ---
    col1, col2 = st.columns(2)
    with col1:
        name      = st.text_input("Full Name", value=profile.get("name", ""))
        school    = st.text_input("School", value=profile.get("school", ""))
        degree    = st.text_input("Degree", value=profile.get("degree", ""))
    with col2:
        gpa       = st.number_input("GPA", min_value=0.0, max_value=4.0,
                                    step=0.01, value=profile.get("gpa", 0.0))
        years_exp = st.number_input("Years of Experience", min_value=0,
                                    max_value=20, step=1,
                                    value=profile.get("years_exp", 0))
        ml_focus  = st.text_input("ML/NLP Focus Area",
                                  value=profile.get("ml_focus", ""))

    st.divider()

    # --- Full-width fields for long text ---
    skills = st.text_area("Skills (comma-separated)", height=80,
                          value=profile.get("skills", ""),
                          help="e.g. Python, PyTorch, LLM fine-tuning, RAG")
    bio    = st.text_area("Bio / Profile Summary", height=150,
                          value=profile.get("bio", ""),
                          help="Used verbatim as context in every Claude email draft. "
                               "Write in first person, under 200 words.")

    submitted = st.form_submit_button("Save Profile", type="primary")
```

### Field specifications

| Field | Widget | Type | Validation |
|-------|--------|------|-----------|
| Full Name | `st.text_input` | str | Non-empty on save |
| School | `st.text_input` | str | Non-empty on save |
| Degree | `st.text_input` | str | e.g. "MS Data Science" |
| GPA | `st.number_input` | float 0.0–4.0 | Clamp to range |
| Years of Experience | `st.number_input` | int 0–20 | Clamp to range |
| ML/NLP Focus Area | `st.text_input` | str | Optional |
| Skills | `st.text_area` | str | Optional; stored as raw text |
| Bio | `st.text_area` | str | Optional; stored as raw text; 200-word soft limit shown in `help` |

### Post-submit feedback

```python
if submitted:
    if not name or not school:
        st.error("Full Name and School are required.")
    else:
        save_profile(profile_data)   # DB write
        st.success("Profile saved.")
        st.toast("Profile saved.", icon="✅")
```

No page reload — `st.success` appears inline below the button. `st.toast` appears
in the lower-right corner simultaneously.

---

## Session State Initialization

Every page must call a shared `init_session_state()` function as its **second call**
(after `set_page_config`). This prevents `KeyError` when Streamlit renders a page
cold (user navigates directly by URL).

```python
# utils/session.py
import streamlit as st

SESSION_DEFAULTS = {
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
    for key, default in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default
```

All page files import and call `init_session_state()` before any data reads.

---

## Spacing Conventions

Streamlit does not use an 8-point spacing system via config. Apply spacing through
these conventions:

| Technique | When to Use |
|-----------|-------------|
| `st.divider()` | Between major form sections, between page title and content |
| `st.write("")` | Single blank line between widgets when vertical breathing room is needed |
| `st.columns([1, 0.05, 1])` | Thin center column as a visual gutter between two data columns |
| `st.container()` | Group related widgets to scope layout without custom CSS |

**Touch target rule:** All `st.button` and `st.form_submit_button` calls use the
default Streamlit button height. Do not shrink buttons via CSS. Minimum effective
click area is Streamlit's default (~36px height).

**Column gutters:** Use `st.columns(2)` with default gutter. Do not specify a
`gap` parameter — Streamlit's default gap is sufficient for a data-dense layout.

---

## Status and Feedback Patterns

| Situation | Widget | Notes |
|-----------|--------|-------|
| Async operation in progress | `st.spinner("Searching...")` | Wrap Claude API calls and DB queries > 0.5s |
| Success confirmation | `st.success("...")` + `st.toast("...", icon="✅")` | Both together — success persists on page, toast auto-dismisses |
| Validation error | `st.error("...")` | Inline, below the triggering form or button |
| Informational / coming-soon | `st.info("...")` | Shell pages; neutral, no action required |
| Warning / non-blocking issue | `st.warning("...")` | Use sparingly — only for data quality warnings |
| Long-running button | Disable via `st.session_state` flag | Set `discover_running = True` on click; button disabled while True |

**Spinner pattern:**

```python
with st.spinner("Claude is searching..."):
    results = claude_discover(filters)
st.session_state["discover_results"] = results
```

**Button disable pattern:**

```python
st.button(
    "Discover",
    disabled=st.session_state["discover_running"],
    on_click=lambda: st.session_state.update({"discover_running": True}),
)
```

---

## Status Badge Colors (for Phase 4 — defined here for consistency)

Badges are rendered via `st.markdown` with inline `background-color` spans.
Define the color map once in `utils/badges.py` so all pages use the same values.

| Status | Background | Text | Hex (bg) |
|--------|-----------|------|----------|
| Not Contacted | `#e5e7eb` | `#374151` | Gray |
| Drafted | `#fef3c7` | `#92400e` | Amber |
| Sent | `#dbeafe` | `#1e40af` | Blue |
| Replied | `#d1fae5` | `#065f46` | Green |
| Interview | `#16a34a` | `#ffffff` | Dark green |
| Rejected | `#fee2e2` | `#991b1b` | Red |

```python
STATUS_COLORS = {
    "Not Contacted": {"bg": "#e5e7eb", "text": "#374151"},
    "Drafted":       {"bg": "#fef3c7", "text": "#92400e"},
    "Sent":          {"bg": "#dbeafe", "text": "#1e40af"},
    "Replied":       {"bg": "#d1fae5", "text": "#065f46"},
    "Interview":     {"bg": "#16a34a", "text": "#ffffff"},
    "Rejected":      {"bg": "#fee2e2", "text": "#991b1b"},
}

def status_badge(status: str) -> str:
    c = STATUS_COLORS.get(status, {"bg": "#e5e7eb", "text": "#374151"})
    return (
        f'<span style="background-color:{c["bg"]};color:{c["text"]};'
        f'padding:2px 8px;border-radius:4px;font-size:13px;font-weight:600;">'
        f'{status}</span>'
    )
```

Call `st.markdown(status_badge(row["status"]), unsafe_allow_html=True)` in tracker
table rows. Do NOT use this pattern for anything other than status badges — minimize
`unsafe_allow_html=True` usage to this one utility function.

---

## Copywriting Contract

### App-level

| Element | Copy |
|---------|------|
| App title (sidebar) | `Outreach CRM` |
| Sidebar subtitle | `AI/ML Startup Outreach` |
| Browser tab title | `Outreach CRM` |

### My Profile page

| Element | Copy |
|---------|------|
| Page title | `My Profile` |
| Page description | `Your background is used as context in every email Claude drafts. Keep it current.` |
| Primary CTA | `Save Profile` |
| Success message | `Profile saved.` |
| Toast | `Profile saved.` |
| Error — missing required | `Full Name and School are required.` |
| Bio field help text | `Used verbatim as context in every Claude email draft. Write in first person, under 200 words.` |
| Skills field help text | `e.g. Python, PyTorch, LLM fine-tuning, RAG` |
| Empty profile state | `Fill in your profile before starting outreach — Claude uses this to personalize every email.` (render as `st.info(...)` if profile is empty on first load) |

### Shell pages (Phase 1 only)

| Page | Copy |
|------|------|
| Discover | `Coming soon — built in Phase 2.` |
| Contacts | `Coming soon — built in Phase 3.` |
| Draft Email | `Coming soon — built in Phase 3.` |
| Tracker | `Coming soon — built in Phase 4.` |
| Dashboard | `Coming soon — built in Phase 4.` |

All shell copy renders as `st.info("Coming soon — built in Phase N.")`. No additional
widgets, headers, or placeholder content on shell pages beyond `st.title()` and the
`st.info()` banner.

### Destructive actions in Phase 1

None. My Profile has no delete action. No confirmation dialogs required in Phase 1.

---

## Registry

Not applicable. This is a Python/Streamlit project. No shadcn, no npm component
registry. Safety gate: not applicable.

---

## Pre-Population Sources

| Decision | Source |
|----------|--------|
| App name "Outreach CRM" | User input (this session) |
| Light theme, white/light gray | User input (this session) |
| Primary color #3b82f6 | User input (this session) |
| Wide layout | REQUIREMENTS.md — "data-dense tables, filters" / PROJECT.md "functional and data-dense" |
| 6 pages: Discover, Contacts, Draft Email, Tracker, Dashboard, My Profile | REQUIREMENTS.md FOUND-02 |
| My Profile fields: name, school, degree, GPA, years exp, skills, ML/NLP focus, bio | REQUIREMENTS.md FOUND-03 |
| Two-column layout for short fields | User input (this session) |
| Shell pages use st.info("Coming soon") | User input (this session) |
| Status badge set | REQUIREMENTS.md TRACK-01 — defined here for consistency across phases |
| Session state keys | Derived from all phase requirements — pre-initialize all to prevent KeyError (ROADMAP success criterion 3) |
| st.form for My Profile | REQUIREMENTS.md / architecture — single DB write on submit, not per-keystroke |

---

*UI-SPEC status: draft — ready for gsd-ui-checker validation.*

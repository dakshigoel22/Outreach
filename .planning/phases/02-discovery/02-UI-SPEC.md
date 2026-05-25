---
phase: 2
slug: discovery
status: approved
shadcn_initialized: false
preset: none
created: 2026-05-25
author: gsd-ui-researcher
---

# UI-SPEC: Phase 2 — Discovery

> Extends the Phase 1 design system. The Discover page is the primary entry point for the
> outreach workflow — it must feel fast, focused, and actionable. All color, typography,
> spacing, and component conventions from Phase 1 are inherited and extended here.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | None (Streamlit native — Python project) |
| Preset | not applicable |
| Component library | Streamlit built-ins only |
| Icon library | Streamlit emoji strings (`:white_check_mark:`, `:mag:`) |
| Font | Sans-serif (system stack via `.streamlit/config.toml`) |

**No new styling mechanisms introduced.** Phase 1 established `st.markdown` with
`unsafe_allow_html=True` only for status badges (one callsite in `utils/badges.py`).
Phase 2 adds one more: the "Saved ✓" badge on company cards. All other UI uses
Streamlit native components only.

---

## Color Palette (inherited from Phase 1)

All colors are already defined in `.streamlit/config.toml` and `utils/badges.py`.
Phase 2 adds one new badge variant:

| Role | Hex | Where Used |
|------|-----|-----------|
| Primary | `#3b82f6` | Discover button, Save button (primary type), links |
| Background | `#ffffff` | Main canvas |
| Secondary Background | `#f0f2f6` | Company cards (use `st.container()` with the page's secondary background), filter section |
| Text | `#1a1a2e` | All body copy, card content |
| Success | `#16a34a` | "Saved ✓" badge background — same as Interview badge |
| Success text | `#ffffff` | "Saved ✓" badge text — same as Interview badge |
| Error | `#dc2626` | `st.error()` for Claude API failures |
| Info | `#3b82f6` | `st.info()` for empty-state instructions |

**"Saved ✓" badge spec (extends `utils/badges.py` pattern):**

```python
SAVED_BADGE_HTML = (
    '<span style="background-color:#16a34a;color:#ffffff;'
    'padding:4px 8px;border-radius:4px;font-size:13px;font-weight:600;">'
    'Saved &#10003;</span>'
)
```

Use `html.escape` on any dynamic content. This badge value is static so no escaping
needed — but the function must not accept user input directly.

---

## Spacing (inherited from Phase 1)

| Technique | When to Use |
|-----------|-------------|
| `st.divider()` | Between filter section and results section; between page title and filters |
| `st.columns(3)` | Three-column grid for company cards (desktop-width layout) |
| `st.columns(2)` | Two-column filter row (location + tier in one row; role type + button in next) |
| `st.write("")` | Single blank line before/after card metadata lines |
| `st.container()` | Wrap each company card to scope visual boundary |

**Card grid:** Three columns (`st.columns(3)`) is the standard for this app width
(`layout="wide"`). Do not use `st.columns(4)` — card content (roles list, website URL)
wraps badly at 4 columns. Fall back to `st.columns(2)` only if there are fewer than
3 results.

---

## Typography (inherited from Phase 1)

No new type sizes. All existing Streamlit calls apply:

4 type levels maximum (Streamlit hierarchy, inherited from Phase 1):

| Level | Streamlit Call | Size (approx) | Weight |
|-------|---------------|---------------|--------|
| Display | `st.title("Discover")` | ~28px | Bold (700) |
| Section | `st.subheader(...)` | ~16px | Semibold (600) |
| Body | `st.write(...)` and `st.markdown(f"**{name}**")` | ~16px | Regular (400) or Bold (700) — same size, two weights |
| Caption | `st.caption(...)` | ~13px | Regular (400) |

Company name uses `st.write(f"**{html.escape(company.name)}**")` (bold body weight) — same size level as regular card metadata, not a separate level. Two weights within the body level are permitted (see Phase 1: "Two weights only: Regular (400) for body/labels, Bold/Semibold (600–700) for headings").

No `st.header()` on this page — it would create a 5th level and break the 4-level max.

---

## Page Layout — Discover (`pages/1_Discover.py`)

### File header (mandatory)

```python
import streamlit as st
from utils.session import init_session_state

st.set_page_config(
    page_title="Outreach CRM",
    page_icon=":outbox_tray:",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()
```

### Section 1 — Page title

```python
st.title("Discover")
st.caption("Find AI/ML startups matching your target. Claude searches the web and returns live results.")
st.divider()
```

### Section 2 — Filters

Two-row layout. Row 1: location + tier. Row 2: role type (full width for readability).
Discover button sits in its own row below the filters to give it visual prominence.

```python
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
```

Persist selected values to `SESSION_DEFAULTS` — add these keys:
- `"discover_location"` → `"NYC"` (first option default)
- `"discover_tier"` → `"Both"` (broadest default)
- `"discover_role_type"` → `"Both"` (broadest default)

### Section 3 — Discover button

```python
discover_clicked = st.button(
    "Discover",
    type="primary",
    disabled=st.session_state["discover_running"],
    use_container_width=False,
)
```

**Width rule:** Do NOT set `use_container_width=True` — a full-width button is
visually ambiguous (looks like a form submit). Leave it at natural width (~120px).

**State management:** On click, set `discover_running = True` before the Claude call,
`False` in a `finally` block after (even on error). Pattern:

```python
if discover_clicked:
    st.session_state["discover_running"] = True
    try:
        with st.spinner("Claude is searching..."):
            results = discover_companies(filters)
        st.session_state["discover_results"] = results
        st.session_state["discover_running"] = False
        st.rerun()
    except Exception as e:
        st.session_state["discover_running"] = False
        st.error(f"Search failed: {e}")
```

### Section 4 — Empty state (no results yet)

Displayed when `st.session_state["discover_results"]` is empty AND
`discover_running` is False (not during a search):

```python
if not st.session_state["discover_results"] and not st.session_state["discover_running"]:
    st.info(
        "Set your filters above and click **Discover** to find AI/ML startups. "
        "Claude will search the web and return live results."
    )
```

No table, no placeholder cards, no spinner. Just the `st.info` banner.
The CTA (Discover button, already rendered above) is the dominant element.

### Section 5 — Results

Displayed when `discover_results` is non-empty. Duplicate check happens here:

```python
results = st.session_state["discover_results"]
if results:
    st.subheader(f"Results ({len(results)})")
    st.caption("Click Save to add a company to your pipeline.")
    st.divider()

    # Duplicate check: batch query by name + url
    saved_names, saved_urls = get_saved_company_identifiers()  # returns two sets
    cols = st.columns(3)
    for i, company in enumerate(results):
        with cols[i % 3]:
            render_company_card(company, saved_names, saved_urls)
```

---

## Company Card Design

Each card is a visual unit. Use `st.container()` with a visual separator underneath
(not a border — Streamlit doesn't support border styling on containers natively).
Keep it minimal: one `st.divider()` between each row of 3 cards, NOT between every card.

```python
def render_company_card(company, saved_names: set, saved_urls: set) -> None:
    with st.container():
        st.write(f"**{html.escape(company.name)}**")
        st.write(f"Stage: {company.funding_stage}  |  Headcount: {company.headcount}")
        st.write(f"Focus: {company.ai_focus}")
        if company.website:
            st.write(f"[{company.website}]({company.website})")
        if company.hiring_roles:
            st.caption(f"Roles: {', '.join(company.hiring_roles)}")

        is_saved = (
            company.name.lower() in saved_names
            or (company.website and company.website.rstrip("/") in saved_urls)
        )
        if is_saved:
            st.markdown(SAVED_BADGE_HTML, unsafe_allow_html=True)
        else:
            if st.button("Save", key=f"save_{i}_{company.name}"):
                save_company(company)
                st.success(f"{company.name} saved.")
                st.rerun()
    st.write("")  # breathing room between cards in same column
```

**Card field order (top to bottom):**
1. Company name (bold)
2. Funding stage | Headcount (single line, `|` separator)
3. AI focus
4. Website link (only if present)
5. Hiring roles (caption weight — less prominent)
6. Save button or Saved badge

**No card borders, no `st.expander`, no nested tabs** — keep cards flat and scannable.

---

## Duplicate Badge Spec

| State | Visual |
|-------|--------|
| Not saved | `st.button("Save", type="primary")` — blue button |
| Already saved | `SAVED_BADGE_HTML` span + no button | 

The Save button for an already-saved company is replaced entirely by the badge. It is NOT
a disabled button (disabled buttons show a muted label — visually unclear). The badge
communicates finality.

---

## Spinner and Loading State

**Text:** `"Claude is searching..."` — not "Loading..." or "Please wait...".
**Scope:** Wraps the entire Claude API call only (not the duplicate check).
**Placement:** Appears in-page where the results section will be, not in the sidebar.

```python
with st.spinner("Claude is searching..."):
    results = discover_companies(filters)
```

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Page title | `Discover` |
| Page caption | `Find AI/ML startups matching your target. Claude searches the web and returns live results.` |
| Filter section label — location | `Location` |
| Filter section label — tier | `Tier` |
| Filter section label — role type | `Role Type` |
| Primary CTA | `Discover` |
| Spinner text | `Claude is searching...` |
| Empty state (no results) | `Set your filters above and click **Discover** to find AI/ML startups. Claude will search the web and return live results.` |
| Results subheader | `Results ({N})` where N = count |
| Results caption | `Click Save to add a company to your pipeline.` |
| Save button | `Save` |
| Saved badge | `Saved ✓` |
| Post-save success | `{company.name} saved.` |
| Claude API error | `Search failed: {error message}` |
| Discover button — disabled state copy | `Discover` (same — button is just visually disabled, no label change) |

---

## Session State Keys Added in Phase 2

Add to `SESSION_DEFAULTS` in `utils/session.py`:

| Key | Default | Type |
|-----|---------|------|
| `"discover_location"` | `"NYC"` | str |
| `"discover_tier"` | `"Both"` | str |
| `"discover_role_type"` | `"Both"` | str |

Keys `"discover_results"` and `"discover_running"` already exist in Phase 1.

---

## New Module: `services/__init__.py` + `services/claude.py`

Phase 2 introduces the `services/` package. The Anthropic client must be wrapped in
`@st.cache_resource` so it is created once per Streamlit session and not re-initialized
on every rerun:

```python
# services/claude.py — structural pattern only (implementation in PLAN.md)
import streamlit as st
from anthropic import Anthropic

@st.cache_resource
def get_claude_client() -> Anthropic:
    return Anthropic()  # reads ANTHROPIC_API_KEY from env
```

---

## Error States

| Scenario | Widget | Copy |
|----------|--------|------|
| Claude API call fails (any exception) | `st.error(...)` | `Search failed: {exception message}` |
| Zero results returned | `st.warning(...)` | `No matching companies found. Try adjusting your filters or broadening the tier.` |
| JSON parse / pydantic validation fails | `st.error(...)` | `Unexpected response from Claude. Please try again.` |

Zero results is a warning, not an error — the user needs to adjust filters, not report a bug.

---

## Registry Safety

Not applicable. This is a Python/Streamlit project. No shadcn, no npm registry,
no JavaScript component libraries. Safety gate: not applicable.

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: FLAG (non-blocking — "Save" single-word CTA)
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: FLAG (non-blocking — 60/30/10 ratio implicit, not labeled)
- [x] Dimension 4 Typography: FLAG (non-blocking — body line-height not stated; Streamlit default ~1.5)
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-05-25

---

## Pre-Population Sources

| Decision | Source |
|----------|--------|
| Color palette | Phase 1 UI-SPEC (inherited, no changes) |
| Typography | Phase 1 UI-SPEC (inherited, no changes) |
| Spacing conventions | Phase 1 UI-SPEC (inherited, no changes) |
| `st.set_page_config` pattern | Phase 1 UI-SPEC |
| `init_session_state()` as second call | Phase 1 UI-SPEC |
| Discover button disable pattern | Phase 1 UI-SPEC (spinner + session state flag) |
| `@st.cache_resource` for Claude client | CONTEXT.md code_context §Established Patterns |
| Filter options (NYC / Arlington VA / DC / SF, Tier 2/3/Both, Internship/Full-time/Both) | CONTEXT.md §Specifics + DISC-01 |
| 3-column card grid | Layout analysis — `layout="wide"` + 5–10 result cards |
| "Saved ✓" badge replaces button (not disabled state) | CONTEXT.md D-10 |
| Batch duplicate check (single query, not per-card) | CONTEXT.md D-09 |
| Results persist across navigation | CONTEXT.md D-05 |
| No auto-retry on sparse results | CONTEXT.md D-04 |
| Zero-results → `st.warning`, not `st.error` | UX heuristic — not a failure state |

---

*UI-SPEC status: draft — ready for gsd-ui-checker validation.*

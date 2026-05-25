# Project Research Summary

**Project:** Recruiter Outreach CRM
**Domain:** Local Python + Streamlit CRUD app with Anthropic AI and Gmail MCP integration
**Researched:** 2026-05-24
**Confidence:** MEDIUM (training-data-only research; key API details need live verification)

---

## Executive Summary

This is a single-user local CRM built to eliminate the spreadsheet-and-copy-paste workflow for AI/ML startup cold outreach. The core loop is: Claude discovers companies and contacts via web search → user reviews and adds context → Claude drafts a personalized email → Gmail MCP sends it → a Streamlit tracker keeps the pipeline visible. The entire stack (Python + Streamlit + SQLite + Anthropic SDK + Gmail MCP) is fixed by constraint, and research confirms that stack is well-matched to the problem — no alternatives are needed.

The recommended build approach is strictly layered: a `db.py` data foundation first, then a thin service layer (one file per domain: discovery, contacts, email, tracker, export), then thin page files that only call services. Pages never touch SQLite directly. This discipline is not optional — Streamlit's rerun model makes any shortcut here into a debugging nightmare within days. Session state must be initialized globally from a shared `utils/state.py` module called at the top of every page, or cross-page navigation will produce cryptic KeyErrors.

The two highest risks are (1) the Gmail MCP subprocess lifecycle, which is non-standard and under-documented for Streamlit apps, and (2) the Anthropic web_search tool type string, which is versioned and will break if copied from training data without checking the live docs. Both must be verified before writing any code. Everything else in the stack has HIGH-confidence, well-documented patterns.

---

## Key Findings

### Recommended Stack

The stack is fully constrained by PROJECT.md. Research validates each choice is appropriate and identifies the critical configuration details needed to avoid the most common failure modes.

**Core technologies:**

- **Python 3.11+** — runtime; 3.11 is the sweet spot for dependency compatibility
- **Streamlit 1.35+** — UI layer; `st.data_editor` (stable since 1.23) handles inline CRM editing natively; multipage via `pages/` is first-class
- **Anthropic SDK 0.28+** — Claude API and web_search tool; the built-in `web_search` tool runs server-side and returns results as `end_turn`, not a `tool_use` stop requiring client resolution
- **SQLite (stdlib)** — zero-config, right-sized for thousands of contacts; must enable WAL mode at init and use `check_same_thread=False` with `@st.cache_resource`
- **pandas 2.1+** — required by `st.data_editor`; Copy-on-Write default avoids silent mutation bugs
- **pydantic 2.x** — validate Claude's JSON output before writing to DB; Claude web_search responses are unstructured
- **tenacity 8.x** — exponential backoff for Anthropic API calls; rate limits are real during multi-company discovery runs
- **Gmail MCP server** (Node.js) — official `@modelcontextprotocol/server-gmail`; must be managed as a singleton in Streamlit to avoid zombie subprocesses; requires Google OAuth2 credentials

**Critical version notes to verify before writing code:**
- Anthropic web_search tool type string (e.g., `"web_search_20250305"`) — versioned, verify at https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search-tool
- Current Claude model names — verify at https://docs.anthropic.com/en/docs/about-claude/models
- `mcp` Python package API — relatively new, verify at https://pypi.org/project/mcp/

### Expected Features

**Must have (table stakes) — ship before any other feature:**
- Contact list with inline status update (Not Contacted / Drafted / Sent / Replied / Interview / Rejected)
- Add contact manually with source badge (AI-discovered vs. manual)
- View all contacts per company
- Email drafting per contact with email type selector (internship / full-time / networking / follow-up)
- Gmail send with draft review step before dispatch
- Auto-update status to "Sent" on successful Gmail dispatch
- Notes per contact (freetext, inline editable)
- Filter tracker by status
- My Profile settings page (gates all drafting quality)
- Company list with tier badge (Tier 2 / Tier 3)
- Claude company discovery via web_search

**Should have (differentiators — high value, build in weeks 2-3):**
- Email type selector changing Claude's prompt strategy (not just a label)
- Contact completeness gating (Draft Email button disabled if email field empty)
- "What Claude knows" collapsible panel showing personalization inputs
- Days-in-stage indicator (requires events/status-transition table)
- Dashboard: reply rate, interview conversion, rejection rate by tier
- Filter by location + tier + AI focus + status simultaneously
- Follow-up flag per contact
- CSV export

**Defer to v2+:**
- Email template library, automated follow-up scheduling, email open/click tracking
- LinkedIn/Crunchbase API integrations, multi-user features, cloud deployment
- A/B testing, contact deduplication/merge UI, calendar integration

**Key insight from features research:** The events table (stage transitions with timestamps, not just a `current_status` column) costs almost nothing in SQLite and is what makes days-in-stage and dashboard metrics possible without a schema migration. Build it from Phase 1 even if the UI for it comes later.

### Architecture Approach

Strict three-layer architecture: Streamlit page files (UI only) → service modules (business logic) → `db.py` (all SQLite). Pages call service functions and read/write `st.session_state`. Service functions call `db.py` or `claude.py` and return plain Python dicts or DataFrames. `db.py` is the only file that imports `sqlite3`. This separation keeps page files thin, makes logic testable, and prevents the most common Streamlit debugging problems.

**Major components:**

1. **`db.py`** — `init_db()` creates all four tables idempotently on startup; all CRUD; WAL mode enabled; `@st.cache_resource` singleton connection with `check_same_thread=False`
2. **`services/claude.py`** — Anthropic client wrapper; `call_with_web_search()` for discovery; `stream_email_draft()` generator for drafting; single `CLAUDE_MODEL` constant defined here
3. **`services/gmail_mcp.py`** — MCP client invocation; accepts `(to, subject, body)`, returns `(success, message_id, error)`; fully encapsulates subprocess lifecycle
4. **`services/discovery.py`** — builds web_search prompt, parses and validates company JSON with pydantic, saves to `companies` table incrementally
5. **`services/email_service.py`** — builds drafting prompt with profile context, stores draft, orchestrates send
6. **`services/tracker.py`** — status transitions, notes updates, aggregate queries; writes to both `contacts.status` and an `events` table
7. **`utils/state.py`** — defines all session state key constants; `initialize_session_state()` called at top of every page
8. **`pages/`** — one thin file per page; never imports `sqlite3`; uses `st.switch_page()` for cross-page navigation with IDs passed via session state

**Four-table schema:** `companies`, `contacts`, `emails`, `events` (status transitions with timestamps). Add four indexes at Phase 1: contacts by company_id, contacts by status, emails by contact_id, emails by status.

### Critical Pitfalls

**Top 5 must-knows — all HIGH confidence:**

1. **`st.data_editor` edited_rows keys are positional DataFrame indices, not DB primary keys.** Set `df = df.set_index("id")` before passing to the editor. With the default integer index, edits on filtered/sorted views silently update the wrong contact in SQLite with no error message.

2. **Session state is not pre-initialized for unvisited pages.** Every page must call `initialize_session_state()` from `utils/state.py` at its top. Pages that assume another page has set a key (e.g., `selected_contact_id`) will throw `KeyError` on first direct navigation. Define all keys with defaults in one shared function.

3. **Anthropic web_search calls block the Streamlit UI for 15-60 seconds and cannot safely be made async.** Mitigation: disable the Discover button via session state while the call is in flight, wrap in `st.status()` spinner, set `anthropic.Anthropic(timeout=httpx.Timeout(120.0))`, and persist results to SQLite immediately on receipt.

4. **SQLite connections must not be shared across Streamlit threads.** Use `with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:` per function call, or a `@st.cache_resource` singleton. Enable `PRAGMA journal_mode=WAL` once at `init_db()`. Never store a `Connection` object in `st.session_state`. Violation produces intermittent "database is locked" errors that correlate with fast user clicks during slow API calls.

5. **Claude web_search returns plausible-but-wrong contact data for small startups.** Names, titles, and emails can be hallucinated or stale. Required mitigations: surface `source_url` alongside every AI-discovered contact, tag them `source="ai_unverified"` with a distinct visual badge, update status to "Sent" only on confirmed Gmail MCP success (never optimistically).

---

## Implications for Roadmap

### Phase 1: Data Foundation + App Skeleton

**Rationale:** Every phase depends on the database and session state infrastructure. Setting connection patterns, schema, and state initialization wrong here requires painful retrofitting across every subsequent phase. The Settings page belongs here too — without profile data, the first email draft will be generic and erode trust in the app.

**Delivers:** Running Streamlit app, all four tables (including `events` for future days-in-stage), correct SQLite connection with WAL mode, typed `load_contacts()` / `save_contact()` helpers, `initialize_session_state()` in `utils/state.py`, DB path via `pathlib`, UNIQUE constraints on natural keys, Settings/My Profile page.

**Avoids:** SQLite threading (C1), pandas type round-trips (M1), relative DB path (N1), session state KeyErrors (C2), double-submit schema gaps (M2).

**Research flag:** Standard patterns — skip research-phase. SQLite + Streamlit connection patterns are HIGH confidence.

---

### Phase 2: Discovery Pipeline

**Rationale:** Discovery is the highest-value differentiator. It also exercises the Anthropic SDK end-to-end, surfacing any API shape surprises before the email flow depends on them. Build before contacts because discovery populates the contacts table.

**Delivers:** `pages/1_Discover.py` with filters, `st.status()` spinner, company result cards with tier badges, "Save company" button. `services/discovery.py` with pydantic-validated prompt/parse/persist cycle. `services/claude.py` with web_search wrapper, timeout config, and `CLAUDE_MODEL` constant.

**Avoids:** Blocking UI (C4 — disabled button + timeout), hallucinated contacts (C5 — `ai_unverified` badge + `source_url`), rate limits (M4 — catch `RateLimitError`, `time.sleep(1)` between company calls, incremental persistence), widget key conflicts (M5 — DB primary key in widget keys).

**Research flag:** Needs research-phase. Anthropic web_search tool type string and built-in tool stop_reason behavior must be verified against live docs before writing `services/claude.py`.

---

### Phase 3: Contacts

**Rationale:** Contacts are the core entity linking companies to emails. Manual add is needed to complement Claude discovery (which will have gaps and unverified data). Prerequisite for email drafting.

**Delivers:** `pages/2_Contacts.py` with contact list per company, manual add form, source badge (AI-discovered vs. manual), contact completeness indicator (email field present check).

**Avoids:** Duplicate contacts on double-submit (M2 — `UNIQUE(email)` constraint already in schema), unmanageable tracker on first load (N4 — default filter `status != "Rejected"`, default sort `updated_at DESC`).

**Research flag:** Standard patterns — skip research-phase.

---

### Phase 4: Email Drafting + Gmail Send

**Rationale:** Drafting requires contacts and a complete profile. Gmail MCP is the highest-risk integration (LOW-MEDIUM confidence); building and debugging it here while the app is small is far easier than bolting it on at the end.

**Delivers:** `pages/3_Email_Drafting.py` with contact selector, email type selector, streaming draft display (token-by-token), editable text area for review, send button. `services/gmail_mcp.py` with full try/except, success-only status update, re-auth instructions on failure. `services/email_service.py` with prompt builder (contact role + company AI product + user profile + email type as inputs).

**Avoids:** Silent Gmail auth failure (M3 — try/except on every MCP call, status updated only on confirmed success), generic drafts from sparse profile (N3 — profile completeness warning before draft button).

**Research flag:** Needs research-phase. Gmail MCP subprocess lifecycle in Streamlit, current `mcp` Python package API, and Gmail MCP server invocation contract must be verified before implementation.

---

### Phase 5: Tracker

**Rationale:** The daily-use surface. Build after all prior phases so the joined query is tested against realistic data (real companies, contacts, and email rows). The `events` table built in Phase 1 makes days-in-stage available here without schema changes.

**Delivers:** `pages/4_Tracker.py` with joined DataFrame, color-coded status badges, inline status dropdown (`df.set_index("id")` pattern), inline notes edit, filter by status/tier/location, row count indicator, default sort `updated_at DESC`, default filter hiding Rejected, days-in-stage column from events table.

**Avoids:** Wrong-row edits (C3 — `df.set_index("id")`), widget key conflicts (M5 — `key=f"status_{contact_id}"`).

**Research flag:** Standard patterns — skip research-phase.

---

### Phase 6: Dashboard + Export

**Rationale:** Aggregates all prior data to surface whether the outreach strategy is working. Requires real pipeline data to be meaningful; building earlier means building against empty tables.

**Delivers:** `pages/5_Dashboard.py` with `st.metric` cards (contacts found, emails sent, reply rate, interview conversion), filter widgets, reply rate broken down by tier, `st.download_button` for CSV via `services/export.py`.

**Avoids:** No new pitfalls; this phase is pure aggregation on existing data.

**Research flag:** Standard patterns — skip research-phase.

---

### Phase Ordering Rationale

- Foundation before everything because SQLite and session state bugs compound across all later phases.
- Discovery before contacts because contacts are populated by discovery; building contact CRUD against empty tables means testing with fake data.
- Drafting before tracker because the tracker's email-history view is only meaningful once real drafts exist.
- Gmail MCP in Phase 4 (not deferred) because it's the highest integration risk; fail early.
- Dashboard last because it aggregates all prior data and is the only phase with no downstream dependencies.

### Research Flags

**Needs research-phase during planning:**
- **Phase 2 (Discovery):** Anthropic web_search tool type string and built-in tool behavior — must verify at https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search-tool before `services/claude.py`.
- **Phase 4 (Gmail Send):** Gmail MCP subprocess lifecycle in Streamlit, `mcp` Python package API, Gmail MCP server invocation contract — verify at https://github.com/modelcontextprotocol/servers before `services/gmail_mcp.py`.

**Standard patterns (skip research-phase):**
- **Phase 1:** SQLite + Streamlit connection patterns are HIGH confidence.
- **Phase 3:** Contact CRUD is standard Streamlit + SQLite.
- **Phase 5:** `st.data_editor` patterns are HIGH confidence and well-documented.
- **Phase 6:** Aggregation queries and Streamlit metric cards are HIGH confidence.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Core Python/Streamlit/SQLite patterns are HIGH; Anthropic web_search tool type string and Gmail MCP Python API are MEDIUM-LOW and must be verified against live docs before implementation |
| Features | MEDIUM | Derived from training-data analysis of Apollo, Lemlist, Outreach.io, Hunter.io, and job-seeker community patterns; no live competitor verification performed |
| Architecture | HIGH | Streamlit multi-page, SQLite WAL, `@st.cache_resource`, session state patterns are all stable, well-documented, and HIGH confidence |
| Pitfalls | HIGH | All five critical pitfalls are documented Streamlit/SQLite/LLM behaviors, not inferences; confidence is HIGH regardless of web access limitation |

**Overall confidence: MEDIUM**

The app's architecture and SQLite/Streamlit patterns are well-understood. The two unknowns that require live verification (Anthropic web_search tool type string, Gmail MCP Streamlit integration) are localized to single service modules and can be resolved in a 30-minute pre-coding verification step.

### Gaps to Address

- **Anthropic web_search tool type string:** Verify at https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search-tool before writing `services/claude.py`. The exact `"type"` value is versioned; training data value may be outdated. This is the single most important pre-code check.
- **Current Claude model IDs:** Verify at https://docs.anthropic.com/en/docs/about-claude/models before any `client.messages.create()` call. Define as a single `CLAUDE_MODEL` constant in `services/claude.py`.
- **Gmail MCP Python client API:** Verify at https://pypi.org/project/mcp/ and https://github.com/modelcontextprotocol/servers before Phase 4. The invocation API may differ from training data.
- **Gmail MCP token refresh behavior:** Verify whether the server auto-refreshes OAuth tokens or requires user re-authentication flow. Determines error handling UX in Phase 4.
- **Anthropic rate limit tiers:** Check current per-minute limits for the model in use before Phase 2. Calibrate the sleep-between-calls duration accordingly.

---

## Sources

### Primary (HIGH confidence)
- Streamlit official docs (multi-page, `st.data_editor`, `st.cache_resource`, session state) — architecture and pitfall patterns
- SQLite official docs (WAL mode, threading model) — connection patterns
- Anthropic Python SDK docs (streaming, tool use shape) — SDK patterns
- PROJECT.md (local) — requirements, constraints, user context

### Secondary (MEDIUM confidence)
- Training-data knowledge of Apollo.io, Lemlist, Outreach.io, Hunter.io feature sets as of August 2025 — feature benchmarking
- Community patterns from r/cscareerquestions, Blind, LinkedIn — job-seeker spreadsheet baseline and pain points
- Cold email effectiveness research (Woodpecker, Lemlist, Reply.io) — email prompt design guidance

### Tertiary (LOW confidence — verify before implementation)
- Anthropic web_search built-in tool API shape — training data; versioned type string must be confirmed against live docs
- Gmail MCP server Streamlit integration topology — inferred from general MCP client patterns; verify against actual server docs
- Anthropic rate limit thresholds — training data; changes frequently, check before Phase 2

---

*Research completed: 2026-05-24*
*Ready for roadmap: yes*

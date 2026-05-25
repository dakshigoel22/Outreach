# Phase 2: Discovery - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 delivers the AI-powered company discovery pipeline: user sets location/tier/role filters, clicks Discover, Claude uses web_search to find 5–10 matching AI/ML startups, results display as cards in the app, and user saves any company to the DB with one click. Already-saved companies are visually distinguished so duplicates are prevented.

This phase does NOT include contact discovery, email drafting, or search history storage — those belong to Phase 3 and future phases.

</domain>

<decisions>
## Implementation Decisions

### Claude API Pipeline
- **D-01:** Claude must return a **JSON array** of company objects. The prompt instructs Claude to respond with structured JSON (not prose). The service validates the output with pydantic before writing to the DB. Do not attempt to parse prose.
- **D-02:** The Claude call **blocks** the UI with a spinner (`discover_running = True` in session state). No streaming. A single call returns a full batch of results. This matches the `discover_running` flag already initialized in `utils/session.py`.
- **D-03:** Target **5–10 companies per search call**. Prompt should request this range explicitly.
- **D-04:** If Claude returns fewer results than expected (even 1–2), show whatever was found. No auto-retry. Let the user decide whether to search again with adjusted filters.

### Result Persistence
- **D-05:** Discover results **persist in session state** (`discover_results`) until a new search runs. User can navigate to other pages and return to see their last results. Do not clear on navigation.
- **D-06:** Filter selections (location, tier, role type) also **persist in session state**. Add filter keys to `SESSION_DEFAULTS` in `utils/session.py` (e.g., `discover_location`, `discover_tier`, `discover_role_type`).
- **D-07:** First-load empty state (no search run yet): show filter widgets and a prominent Discover button with brief instructions. No empty table or list container. The CTA is the dominant element.

### Duplicate Detection
- **D-08:** A company is considered "already saved" if **either** the name (case-insensitive) OR the website URL matches a row in the `companies` table. Both fields checked — name match OR URL match is a hit.
- **D-09:** Run the duplicate check **once after results load** using a single batch query (SELECT with IN clause on names + urls). Do not run per-card queries.
- **D-10:** Visual indicator for already-saved companies: **"Already saved" badge + disabled Save button**. Use a green "Saved ✓" badge in place of the Save button. Card remains fully readable.

### Claude's Discretion
- Exact prompt wording and system prompt structure for the web_search call — researcher should verify the current web_search tool type string and model ID from live docs before drafting the prompt.
- Pydantic model field names and validation rules for the company JSON.
- URL normalization strategy for URL-based duplicate detection (strip trailing slash, normalize http/https).
- Number of web_search calls per Discover run (single call vs. multiple targeted calls).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### External — MUST verify before coding (research flag from ROADMAP.md)
- Anthropic web_search tool type string: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search-tool — the type string (e.g. `"web_search_20250305"`) is versioned; training-data values may be stale. Verify before writing `services/claude.py`.
- Current Claude model IDs: https://docs.anthropic.com/en/docs/about-claude/models — verify the model ID before any `client.messages.create()` call.

### Project files
- `CLAUDE.md` — project constraints (Anthropic SDK only, no third-party AI APIs, SQLite only)
- `.planning/REQUIREMENTS.md` §Discovery — DISC-01, DISC-02 (authoritative requirement text)
- `database/schema.py` — `companies` table schema (id, name, funding_stage, headcount, website, ai_focus, location, tier, hiring_roles, saved_at)
- `database/connection.py` — `get_connection()` cached connection pattern; all DB access must use this
- `utils/session.py` — `SESSION_DEFAULTS` dict; new filter keys must be added here (not inline in the page)
- `requirements.txt` — existing dependencies; add `anthropic`, `pydantic`, `tenacity`, `python-dotenv` if not already present

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `database/connection.py` → `get_connection()`: all DB reads/writes in Phase 2 must use this cached connection, not open new connections.
- `utils/session.py` → `SESSION_DEFAULTS`: add `discover_location`, `discover_tier`, `discover_role_type`, and keep `discover_results` and `discover_running` (already present).
- `utils/badges.py` → `status_badge()`: pattern for HTML badge rendering — use the same approach for the "Saved ✓" badge on duplicate companies.
- `pages/1_Discover.py`: placeholder file — Phase 2 replaces its contents entirely.

### Established Patterns
- **`@st.cache_resource` for heavy resources**: `get_connection()` uses this; the Anthropic client should also be wrapped in `@st.cache_resource` in `services/claude.py`.
- **`init_session_state()` on every page**: must be the second call after `st.set_page_config()` in `1_Discover.py`.
- **No f-string interpolation in SQL**: established in `schema.py` (T-01-01 pattern); use parameterized queries for all `WHERE name IN (?)` checks.

### Integration Points
- New `services/claude.py` module: Claude client + `discover_companies(filters: dict) -> list[Company]` function. Called by `pages/1_Discover.py`.
- `companies` table in `outreach.db`: Phase 2 performs `INSERT` (save) and `SELECT` (duplicate check) only. No schema changes needed.

</code_context>

<specifics>
## Specific Ideas

- Discover button disabled while `discover_running` is True — already planned in session state; must also re-enable if the Claude call raises an exception (finally block or try/except).
- The "Saved ✓" badge should use the same `html.escape()` pattern as `utils/badges.py` if rendered via `unsafe_allow_html=True`.
- Filter options per DISC-01: location = [NYC, Arlington VA, DC, SF]; tier = [Tier 2, Tier 3, Both]; role type = [Internship, Full-time, Both].

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-Discovery*
*Context gathered: 2026-05-25*

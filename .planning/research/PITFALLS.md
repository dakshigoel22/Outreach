# Domain Pitfalls

**Domain:** Local Python + Streamlit CRM with Anthropic SDK, SQLite, pandas, Gmail MCP
**Researched:** 2026-05-24
**Confidence note:** All tool access (WebSearch, WebFetch, Bash/Context7) was denied in this
environment. Findings are from training knowledge of these specific libraries and their known
issues. Confidence levels are honest about this limitation — cross-check against current
Streamlit changelog and Anthropic API docs before Phase 1 build.

---

## Critical Pitfalls

Mistakes that cause rewrites, data loss, or the app becoming unusable.

---

### Pitfall C1: SQLite "database is locked" in Streamlit's Threaded Model

**What goes wrong:** Streamlit runs each user session in a separate thread. If you open a
SQLite connection at module level (or use a global connection object), concurrent re-runs
(which Streamlit triggers aggressively) will hit "database is locked" errors. Even with a
single user, Streamlit can trigger multiple simultaneous script executions — for example,
when a widget fires while a slow Claude API call is still running in a `st.spinner`.

**Why it happens:** SQLite's default `check_same_thread=True` raises immediately if any
thread other than the creator touches the connection. Setting `check_same_thread=False`
without a lock is equally dangerous because SQLite in WAL mode handles reads concurrently
but writes are still serialized, and the Python sqlite3 module offers no built-in thread pool.

**Consequences:** Silent write failures, corrupted partial writes, or a hard crash mid-session
that leaves the DB in an inconsistent state (e.g., company row written but contacts not).

**Prevention:**
- Create a new connection per function call (not per module or per session). SQLite connections
  are cheap to open for a local file.
- Use `with sqlite3.connect(DB_PATH) as conn:` context managers so commits and closes are
  automatic.
- Add `conn.execute("PRAGMA journal_mode=WAL")` once at DB initialization. WAL mode allows
  concurrent reads while a write is happening, which matches Streamlit's pattern well.
- Never store a `sqlite3.Connection` object in `st.session_state`.

**Warning signs:**
- "database is locked" in the Streamlit error panel
- Intermittent write failures that are hard to reproduce (they correlate with fast user
  clicking while Claude is running)
- Data visible in one page tab but not another after a write

**Phase to address:** Phase 1 (DB initialization). Set the connection pattern correctly from
day one — retrofitting is painful.

---

### Pitfall C2: Streamlit Session State Silently Drops on Page Navigation

**What goes wrong:** In Streamlit multipage apps (the `pages/` directory model), navigating
between pages does NOT clear `st.session_state` — but widget state (values entered in
`st.text_input`, `st.selectbox`, etc.) IS cleared unless explicitly persisted to session
state before navigation. Any value held only in a widget's default or local variable is gone
the moment the user clicks a sidebar nav link.

Additionally, if you initialize a session state key inside a page's script body (e.g.,
`if "results" not in st.session_state: st.session_state.results = []`), this runs on every
re-run of that page. The check prevents overwrite — but the key only exists once the page
has been visited. Pages that assume another page's session state keys exist will throw
`KeyError`.

**Why it happens:** Streamlit's execution model re-runs the entire page script top-to-bottom
on every interaction. Widget state survives only while the widget is actively rendered on the
current page. Session state keys survive cross-page navigation but are not pre-initialized
for pages not yet visited.

**Consequences:**
- User types a company name in Discovery, Claude runs, user navigates to Tracker to check
  something, comes back — discovery results are gone.
- Email draft page assumes `st.session_state["selected_contact"]` exists (set on Tracker page)
  but if the user lands on Email directly, it throws.

**Prevention:**
- Define a `initialize_session_state()` function in a shared `utils/state.py` module that
  sets ALL session state keys with defaults. Call it at the top of every page script.
- Never rely on widget return values across page boundaries. Copy widget values into session
  state explicitly in `on_change` callbacks or immediately after the widget call.
- Use `st.session_state` as the single source of truth for any data that must survive
  navigation (discovery results, selected contact, draft email text).

**Warning signs:**
- `KeyError: 'selected_contact'` or similar in the Streamlit traceback
- Users report "the results disappeared" after clicking something
- Forms that appear to submit but produce no effect (state was dropped mid-re-run)

**Phase to address:** Phase 1 (app skeleton and routing). Establish the state initialization
pattern before building any feature pages.

---

### Pitfall C3: st.data_editor Edited Rows Use DataFrame Integer Index, Not DB Primary Key

**What goes wrong:** `st.data_editor` returns a dict with keys `"edited_rows"`,
`"added_rows"`, `"deleted_rows"`. The keys in `"edited_rows"` are the **integer row positions
in the DataFrame passed to the widget** — not the `id` column value from your SQLite table.
If the DataFrame is filtered, sorted, or paginated, row position 0 in the editor is not
necessarily row `id=1` in the DB.

**Why it happens:** `st.data_editor` is a display widget, not a DB-aware grid. It operates
on the DataFrame it received, and row identity is positional, not keyed.

**Consequences:**
- Inline status update writes to the wrong contact's row in SQLite.
- Deletes or edits silently succeed against the wrong record.
- The bug is invisible to the user (no error, wrong data updated).

**Prevention:**
- Always keep the `id` column in the DataFrame passed to `st.data_editor` (you can hide it
  from display using `column_config` but keep it in the data). Then when processing
  `edited_rows`, map positional index back to the DataFrame row and extract `df.iloc[row_idx]["id"]`
  to build the `UPDATE` statement.
- Alternatively, set the DataFrame index to `id` before passing to `data_editor`
  (`df = df.set_index("id")`). The edited_rows keys will then be the actual `id` values.
  This is the cleaner approach — prefer it.
- Write a single `apply_edits(df, edited_rows)` helper function that encapsulates this
  mapping, so it's not duplicated across the Tracker and any other editable tables.

**Warning signs:**
- Status badge updates seem to "skip" to a different contact
- Filter by status shows stale data for some records after editing
- Edits on filtered/sorted views produce wrong results

**Phase to address:** Phase 2 (Tracker table build). Nail this pattern on first implementation.

---

### Pitfall C4: Anthropic web_search Tool Has No Streaming Progress — Blocking Calls Freeze UI

**What goes wrong:** The Anthropic SDK's `web_search` tool (used inside a `messages.create`
call with `tools=[{"type": "web_search_20250305", ...}]`) can take 15–60 seconds for
multi-step company discovery. Calling this synchronously inside a Streamlit page script
freezes the entire Streamlit UI — the spinner spins but no partial results appear, and if
the call exceeds Streamlit's default script timeout, the session silently dies.

Worse: if the user clicks anything during the wait, Streamlit triggers a re-run. The
in-flight API call is not cancelled — it completes in the background, its results are
discarded, and a second call fires. You can quickly accumulate API credit burn from duplicate
in-flight requests.

**Why it happens:** Streamlit's execution model is synchronous and single-threaded per
session. Long-running blocking calls don't yield control back to the UI layer. Streamlit's
streaming support exists for `write_stream` but requires the upstream call to be a streaming
generator — the Anthropic SDK's tool-use path (multi-turn with `web_search`) does not expose
intermediate tool-call results as a stream.

**Consequences:**
- Discovery page appears hung for 30–60 seconds with no feedback.
- API costs multiply from re-triggered duplicate calls.
- Session can die silently, losing all results.

**Prevention:**
- Wrap all Anthropic SDK calls in `st.spinner("Claude is searching...")` — not a fix, but
  at minimum tells the user to wait.
- Set `disabled=True` on the "Discover" button while a search is in progress using session
  state (`st.session_state["searching"] = True`), and re-enable it in a `finally` block.
  This prevents accidental re-triggers.
- Set an explicit `timeout` in the `httpx` transport layer when constructing the Anthropic
  client: `anthropic.Anthropic(timeout=httpx.Timeout(120.0))`. Default may be shorter.
- Persist results to SQLite immediately upon receipt (not held only in session state), so
  that if the session dies, the data is not lost.
- For the MVP, accept the synchronous blocking behavior. Do NOT attempt to run the call in a
  background thread and poll from Streamlit — this pattern interacts badly with session state
  and is very hard to get right. Address with proper async patterns in a later phase if UX
  demands it.

**Warning signs:**
- Browser shows the Streamlit spinner for >30 seconds with no update
- API usage dashboard shows duplicate calls in the same minute
- `httpx.ReadTimeout` or `anthropic.APITimeoutError` in the terminal logs

**Phase to address:** Phase 2 (Discovery feature). Implement the disabled-button guard and
timeout config from the first iteration. Do not defer this to "polish."

---

### Pitfall C5: Claude web_search Returns Plausible-But-Wrong Contact Data

**What goes wrong:** Claude's web search for recruiter/hiring manager contacts at small
startups frequently returns:
- Names and titles that are real but belong to a different company (name collision)
- LinkedIn URLs that 404 or redirect to a different person
- Email addresses that are guessed patterns (`firstname@company.com`) and unverified
- Outdated contacts (person left the company 6 months ago but web results are stale)
- Hallucinated contacts with no real-world grounding (no source URL provided)

This is not a Claude bug — it is the nature of web search for niche targets. The app will
build a contact list that silently contains garbage data.

**Why it happens:** Web search results for small startups are sparse and often only come from
LinkedIn previews (which don't show full profiles without login), Crunchbase, or old blog
posts. Claude fills gaps with its training data, which can be months stale. There is no
ground truth verification step in the pipeline.

**Consequences:**
- Emails sent to wrong people or non-existent addresses.
- User wastes time on contacts that are irrelevant.
- Trust in the app erodes quickly if the first batch of discovered contacts is mostly wrong.

**Prevention:**
- Always surface the `source_url` from Claude's tool result alongside the contact in the UI.
  Never display a contact without showing where it came from.
- Add a mandatory human review step before any contact becomes "active" — use a status like
  `source="ai_unverified"` and visually distinguish it from manually added contacts.
- Store `confidence_notes` from Claude's response as a field on the contact row.
- Do NOT auto-send emails to AI-discovered contacts without the user explicitly opening and
  reviewing the contact record first. The draft/review flow already enforces this for email,
  but the Tracker should also visually flag unverified contacts.
- Prompt engineering: Instruct Claude to explicitly state when it could NOT find a verified
  recruiter for a company, rather than guessing. "No result" is better than a hallucinated
  result.

**Warning signs:**
- Contacts with no `source_url` in the DB
- Multiple contacts at different companies sharing the same email pattern
- User reports bounced emails from the first send batch

**Phase to address:** Phase 2 (Contact discovery). Build the `ai_unverified` badge and source
URL display from the first implementation. This is not optional polish.

---

## Moderate Pitfalls

---

### Pitfall M1: pandas ↔ SQLite Round-Trip Destroys Data Types

**What goes wrong:** `pd.read_sql("SELECT * FROM contacts", conn)` silently converts:
- `INTEGER` columns to `float64` if any NULL values are present (pandas represents nullable
  integers as float)
- `BOOLEAN`-like columns (stored as 0/1 in SQLite) come back as `int64`, not `bool`
- `DATE`/`DATETIME` TEXT columns come back as `object` (string), not `datetime`
- `None` in SQLite TEXT comes back as `float('nan')` in pandas, which then gets written back
  as the string `"nan"` if you're not careful

**Why it happens:** SQLite is dynamically typed. pandas infers dtypes from the data, and its
inference rules for NULL-containing columns default to float to accommodate NaN.

**Consequences:**
- `st.data_editor` renders a column as a number input when it should be a checkbox, or as
  a text box when it should be a date picker.
- Writing `nan` as a string into a TEXT column corrupts the data.
- Boolean filters (`df[df["is_favorite"] == True]`) silently return empty results when the
  column is `int64`.

**Prevention:**
- Define an explicit dtype map and pass it to `pd.read_sql(..., dtype={...})`.
- Use `pd.Int64Dtype()` (nullable integer) for integer columns that allow NULL.
- After read, explicitly cast: `df["contacted_at"] = pd.to_datetime(df["contacted_at"])`.
- Before writing back to SQLite, replace `float('nan')` with `None`:
  `df = df.where(pd.notna(df), None)`.
- Write a `load_contacts() -> pd.DataFrame` and `save_contact(row: dict)` pair of helper
  functions that enforce types in both directions. Never call `pd.read_sql` raw in page code.

**Warning signs:**
- `st.data_editor` shows `1.0` instead of `True` in boolean columns
- Date columns display as long number strings
- SQLite records show `"nan"` as a string value in a TEXT field

**Phase to address:** Phase 1 (DB schema and data layer). Establish the typed read/write
helpers before any UI is built on top.

---

### Pitfall M2: Streamlit Form Submit Does Not Prevent Double-Submit

**What goes wrong:** `st.form` with `st.form_submit_button` batches widget interactions and
only triggers a re-run on submit. But if the user double-clicks the submit button (common
when the response is slow), Streamlit registers two submit events. The form submit handler
runs twice, potentially inserting duplicate records into SQLite.

**Why it happens:** Streamlit's form submit button does not debounce or disable itself after
the first click at the UI level.

**Consequences:**
- Duplicate company or contact rows in the DB.
- Duplicate email drafts.
- Subtle data integrity issues that are hard to clean up after the fact.

**Prevention:**
- After any form submit that writes to the DB, check for existing records before inserting
  (use `INSERT OR IGNORE` with a UNIQUE constraint, or `SELECT` first).
- Add UNIQUE constraints on natural keys in the schema: `UNIQUE(company_name, location)` for
  companies, `UNIQUE(email)` for contacts (if email is available).
- Disable the submit button via session state while processing (same pattern as C4 above).

**Warning signs:**
- Duplicate rows appearing in the Tracker after rapid form submissions
- User reports "I submitted once and got two results"

**Phase to address:** Phase 1 (DB schema — add UNIQUE constraints) and Phase 2 (form UX —
add disabled state).

---

### Pitfall M3: Gmail MCP Token Refresh Failing Silently Mid-Session

**What goes wrong:** Gmail MCP uses OAuth2 tokens with a 1-hour expiry. If the user starts
a session, leaves the app running in the background, and returns to send an email, the token
may have expired. The MCP call will fail — but if the error is not caught and surfaced
clearly, the user sees nothing happen or a cryptic error, and assumes the send succeeded.

**Why it happens:** OAuth2 access tokens expire by design. The MCP client may not
automatically refresh the token if the refresh flow requires browser interaction (initial
OAuth consent). Background token refresh is only possible if a valid refresh token exists
and the MCP client implements it.

**Consequences:**
- User believes email was sent; it was not.
- No record of failed send in the Tracker.

**Prevention:**
- Wrap all Gmail MCP calls in explicit try/except and surface the error as an `st.error()`
  with a message like "Gmail authentication expired — please re-authenticate."
- Never optimistically mark a contact as "Sent" before the MCP call returns successfully.
  Update the status only in the success branch.
- On first launch, validate the Gmail MCP connection and show a prominent status indicator.
  Do not let the user reach the send flow without knowing the connection is live.
- Document the re-authentication flow (likely: stop app, run `mcp auth gmail`, restart app)
  in the app's help text.

**Warning signs:**
- `401 Unauthorized` or `invalid_grant` in MCP call output
- Tracker shows "Sent" but Gmail Sent folder has no matching email
- MCP call returns immediately with no error but also no confirmation

**Phase to address:** Phase 3 (Gmail MCP integration). Error handling is not optional
polish — build it before any demo or daily use.

---

### Pitfall M4: Anthropic SDK Rate Limits on Rapid Discovery Runs

**What goes wrong:** Running company discovery (which may involve multiple tool-use turns
per session) followed immediately by contact discovery for each company can hit Anthropic's
rate limits. The SDK raises `anthropic.RateLimitError`. If uncaught, the entire Streamlit
page crashes and in-progress results are lost.

**Why it happens:** Discovery for 10 companies with 2–3 web_search tool calls each can
produce 20–30 API calls in a short window. Anthropic enforces per-minute token and request
limits.

**Prevention:**
- Catch `anthropic.RateLimitError` explicitly and surface it as `st.warning()` with a
  "Try again in 60 seconds" message.
- Persist partial results to SQLite immediately as each company or contact is discovered,
  before moving to the next. This way a rate limit hit loses at most one item, not the whole
  batch.
- Add a small `time.sleep(1)` between per-company discovery calls in the loop. This reduces
  burst rate without meaningfully impacting UX (the whole operation is slow anyway).
- Log the raw API error to the terminal so the developer can see what limit was hit.

**Warning signs:**
- `RateLimitError` appearing in terminal after running discovery for >5 companies
- Complete result loss when discovery partially completes
- Error 429 in Streamlit's traceback

**Phase to address:** Phase 2 (Discovery). Add error handling and incremental persistence
from the first working implementation.

---

### Pitfall M5: Streamlit Widget Key Conflicts Across Pages and Re-Renders

**What goes wrong:** Every Streamlit widget that needs a stable identity requires a `key=`
parameter. If two widgets on the same page (or across a multipage app) share a key, Streamlit
raises a `DuplicateWidgetID` error. If a widget's key changes between re-runs (e.g., it's
generated dynamically from a list index), Streamlit treats it as a new widget and resets its
value.

In this app, the Tracker table renders per-row action buttons (e.g., "Edit," "View Draft").
If these buttons use keys like `key=f"edit_{i}"` where `i` is the DataFrame loop index, any
filter that changes the row count shifts all keys, causing ghost clicks.

**Why it happens:** Streamlit uses widget keys to reconcile state across re-runs. Dynamic
key generation from positional indices breaks this reconciliation.

**Prevention:**
- Use the database primary key in widget keys: `key=f"edit_{row['id']}"`. This is stable
  regardless of sort order or filter state.
- Define a key naming convention early: `{page}_{action}_{entity_id}`.
- For `st.data_editor`, the widget itself is one key — do not generate per-row sub-widgets
  inside the editor. Use the editor's callback for all row interactions.

**Warning signs:**
- `DuplicateWidgetID` exception in the Streamlit error panel
- Clicking "Edit" on row 3 opens the edit form for row 7
- Widget values reset unexpectedly when filters are changed

**Phase to address:** Phase 2 (Tracker page). Establish the DB-keyed widget naming
convention before the table is built.

---

## Minor Pitfalls

---

### Pitfall N1: SQLite File Path Is Relative — App Breaks When Run from Different CWD

**What goes wrong:** `sqlite3.connect("outreach.db")` resolves relative to the process
working directory. If the user runs `streamlit run app/main.py` from the repo root vs. from
inside the `app/` directory, the DB file is created (or looked for) in different places.

**Prevention:** Always resolve the DB path relative to the file, not the CWD:
```python
import pathlib
DB_PATH = pathlib.Path(__file__).parent / "data" / "outreach.db"
```
Set this once in a `config.py` module imported everywhere.

**Phase to address:** Phase 1 (project structure).

---

### Pitfall N2: st.data_editor Unsupported Column Types Silently Fall Back

**What goes wrong:** `st.data_editor` does not support all pandas dtypes natively. Columns
with `object` dtype containing mixed types (strings and None) render as text inputs, which
is fine. But columns with `datetime64` render as date pickers only if the column config is
explicitly set. Without config, they may display as raw timestamp integers.

**Prevention:** Use `column_config` explicitly for every non-trivial column in
`st.data_editor`:
```python
st.data_editor(
    df,
    column_config={
        "status": st.column_config.SelectboxColumn(options=STATUS_OPTIONS),
        "last_contacted": st.column_config.DateColumn(),
        "id": st.column_config.Column(disabled=True),
    }
)
```
Define the column config as a module-level constant, not inline, so it's reusable.

**Phase to address:** Phase 2 (Tracker table).

---

### Pitfall N3: Claude Draft Quality Degrades Without Sufficient Profile Context

**What goes wrong:** If the user hasn't filled in their "My Profile" page (background,
resume text, target role), the email drafting prompt sends a sparse context and Claude
produces a generic cold email. The user sees this as the app being low-quality, not as
missing input.

**Prevention:**
- Check that the profile is "complete enough" before enabling the draft button.
  Define minimum required fields: name, current program, graduation date, one-line summary.
- Show a profile completion indicator on the Email page with a link to the Settings page.
- Do not block the user from drafting, but show a `st.warning()` if profile fields are empty.

**Phase to address:** Phase 2 (Email drafting + My Profile settings).

---

### Pitfall N4: Large Discovery Batches Produce Unmanageable Tracker Table

**What goes wrong:** If Claude returns 20 companies with 3 contacts each, the user
immediately has 60 unreviewed rows in the Tracker. The initial sort/filter UX becomes
critical — an unsorted flat list is overwhelming and suggests the app is broken.

**Prevention:**
- Default Tracker sort: `last_updated DESC` so newest additions are at the top.
- Default filter: show only `status != "Rejected"` (hide dead leads by default).
- Show a row count above the table: "Showing 45 of 60 contacts."
- Add a "New (unreviewed)" filter preset for contacts with `source="ai_unverified"` and
  `status="Not Contacted"`.

**Phase to address:** Phase 2 (Tracker). Build default sort/filter from day one.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| DB schema design | Nullable integers become floats in pandas (M1) | Add typed read/write helpers before any page code |
| App skeleton / routing | Session state KeyError on first cross-page nav (C2) | `initialize_session_state()` called at top of every page |
| Tracker table | data_editor row index ≠ DB id (C3) | Set DataFrame index to `id` before passing to editor |
| Tracker table | Widget key conflicts on filter/sort (M5) | Use `f"edit_{row['id']}"` pattern |
| Discovery feature | Blocking Claude call freezes UI (C4) | Disable button, set timeout, persist results incrementally |
| Discovery feature | Rate limit crashes mid-batch (M4) | Catch `RateLimitError`, sleep between calls, persist partial |
| Contact display | AI-hallucinated contacts with no source URL (C5) | Mandatory `source_url` field, `ai_unverified` badge |
| Gmail send flow | Silent auth failure, status marked Sent incorrectly (M3) | Try/except on MCP call, update status only on success |
| Email drafting | Generic drafts from empty profile (N3) | Profile completeness check before enabling draft |
| SQLite initialization | DB file in wrong location when CWD varies (N1) | `pathlib.Path(__file__).parent` for DB path |

---

## Sources and Confidence

| Pitfall | Confidence | Basis |
|---------|------------|-------|
| C1 SQLite threading | HIGH | Well-documented sqlite3 behavior; WAL mode is official recommendation |
| C2 Session state / multipage | HIGH | Core Streamlit execution model, stable across versions |
| C3 data_editor row index | HIGH | Documented in Streamlit data_editor API; `edited_rows` keys are positional |
| C4 Blocking Claude calls | HIGH | Streamlit execution model + Anthropic SDK behavior are both well-documented |
| C5 Hallucinated contacts | HIGH | Fundamental LLM+web_search limitation; not library-version-dependent |
| M1 pandas/SQLite types | HIGH | Long-standing pandas behavior for nullable integer inference |
| M2 Double-submit forms | MEDIUM | Common pattern issue; UNIQUE constraint mitigation is well-established |
| M3 Gmail MCP token expiry | MEDIUM | Standard OAuth2 behavior; MCP-specific refresh behavior unverified (no live docs access) |
| M4 Anthropic rate limits | MEDIUM | Rate limiting exists; exact thresholds change; check current Anthropic API docs |
| M5 Widget key conflicts | HIGH | Documented Streamlit behavior for DuplicateWidgetID |
| N1 Relative DB path | HIGH | Python stdlib behavior, universal |
| N2 data_editor column types | MEDIUM | Behavior observed in Streamlit ≤1.35; verify against current version |
| N3 Profile context quality | MEDIUM | Prompt engineering judgment; not a library issue |
| N4 Tracker UX overload | MEDIUM | UX judgment based on data density requirements in PROJECT.md |

**Items to verify against current docs before Phase 1:**
- Anthropic API rate limit tiers for the claude-3.5-sonnet or claude-3-haiku models (changes frequently)
- Gmail MCP's token refresh behavior — does it auto-refresh or require user intervention?
- Streamlit version in use — `st.data_editor` behavior changed significantly between 1.23 and 1.35

# Architecture Patterns: Recruiter Outreach CRM

**Domain:** Local Python + Streamlit CRUD application with AI integration
**Researched:** 2026-05-24
**Confidence:** HIGH for Streamlit/SQLite patterns (stable, well-documented); MEDIUM for Gmail MCP integration topology (less standardized)

---

## Recommended Architecture

### Layered Structure

```
┌─────────────────────────────────────────────────┐
│                  Streamlit UI Layer              │
│   pages/  (one .py file per page)               │
│   Discover | Contacts | Email | Tracker |        │
│   Dashboard | Settings                           │
└────────────────┬────────────────────────────────┘
                 │ calls
┌────────────────▼────────────────────────────────┐
│               Service Layer                      │
│   discovery.py  contacts.py  email_service.py   │
│   tracker.py    export.py                       │
└──────┬──────────────┬──────────────┬────────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌───▼────────────┐
│  db.py      │ │ claude.py  │ │ gmail_mcp.py   │
│  (SQLite    │ │ (Anthropic │ │ (MCP client    │
│   CRUD)     │ │  SDK)      │ │  wrapper)      │
└──────┬──────┘ └────────────┘ └────────────────┘
       │
┌──────▼──────┐
│ outreach.db │
│ (SQLite)    │
└─────────────┘
```

The key discipline: **pages never touch the database or SDK directly.** Pages call service functions; service functions call db.py or claude.py. This keeps each page file thin (UI only) and makes the logic testable and reusable across pages.

---

## Component Boundaries

| Component | File(s) | Responsibility | Communicates With |
|-----------|---------|----------------|-------------------|
| Pages | `pages/1_discover.py` … `pages/6_settings.py` | Render UI, handle user input, read/write session state | Service layer only |
| Discovery service | `services/discovery.py` | Build Anthropic web_search prompt, parse company JSON, save to DB | claude.py, db.py |
| Contact service | `services/contacts.py` | CRUD for contacts, source badge logic (AI vs manual) | db.py |
| Email service | `services/email_service.py` | Build drafting prompt with profile context, store draft, invoke send | claude.py, gmail_mcp.py, db.py |
| Tracker service | `services/tracker.py` | Status transitions, notes updates, aggregate queries | db.py |
| Export service | `services/export.py` | Build pandas DataFrames from DB, serialize to CSV | db.py |
| DB module | `db.py` | All SQLite reads/writes, schema migration on startup | outreach.db |
| Claude wrapper | `services/claude.py` | Anthropic SDK calls (web_search tool + text generation), streaming helpers | Anthropic API |
| Gmail MCP wrapper | `services/gmail_mcp.py` | MCP client invocation for send, surfaces send result | Gmail MCP server |
| Session state helpers | `utils/state.py` | Typed getters/setters for st.session_state keys, workflow step enum | Streamlit runtime |
| Settings store | `utils/settings.py` | Read/write user profile from a `settings` table or a local JSON sidecar | db.py or local JSON |

### What crosses boundaries

- Pages read `st.session_state` for ephemeral UI state (selected company, current draft, step in wizard).
- Pages call service functions for any DB read/write or AI call — never `sqlite3.connect()` directly.
- Service functions return plain Python dicts or pandas DataFrames — never Streamlit widgets.
- `db.py` is the only module that imports `sqlite3`. Everything else treats it as an opaque dependency.

---

## Data Flow: Discovery → Contacts → Drafting → Sending → Tracking

```
[Discover page]
  User sets filters (location, tier, role type)
       │
       ▼
  discovery.py builds prompt → claude.py calls Anthropic web_search
       │
       ▼ returns list[CompanyDict]
  discovery.py saves to companies table
       │
       ▼
  Page renders company cards from DB query
       │  User clicks "Save company" or "Find contacts"
       ▼
  contacts.py calls claude.py → searches for recruiter/HM at that company
  OR user manually fills add-contact form
       │
       ▼ returns list[ContactDict]
  contacts.py saves to contacts table (source = 'ai' | 'manual')

[Contacts / Email Drafting page]
  User selects contact + email type
       │
       ▼
  email_service.py fetches profile from settings table
  email_service.py builds prompt → claude.py calls Anthropic text generation
       │
       ▼ returns draft string
  email_service.py saves draft to emails table (status = 'drafted')
  Session state: {current_draft, current_contact_id}
       │  User reviews draft in text area, clicks "Send"
       ▼
  gmail_mcp.py sends via MCP → returns message_id or error
  email_service.py updates emails.status = 'sent', sets sent_at timestamp
  contacts.py updates contacts.status = 'Sent'

[Tracker page]
  Reads contacts JOIN emails JOIN companies → pandas DataFrame
  Inline status dropdown → tracker.py updates contacts.status
  Inline notes field → tracker.py updates contacts.notes

[Dashboard page]
  Aggregate SQL queries → summary dicts → st.metric cards
  export.py builds full DataFrame → st.download_button delivers CSV
```

**Direction rule:** Data always flows downward through layers (Page → Service → DB). Results bubble back up as return values, never via side-channel globals.

---

## Database Schema Sketch

```sql
-- Companies discovered or saved by user
CREATE TABLE companies (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    website      TEXT,
    location     TEXT,          -- 'NYC' | 'DC' | 'Arlington VA' | 'SF'
    tier         TEXT,          -- 'Tier2' | 'Tier3'
    funding_stage TEXT,         -- 'Seed' | 'Series A' | 'Series B' | 'Series C'
    headcount_range TEXT,       -- '10-50' | '50-200'
    ai_product   TEXT,          -- short description of their AI/ML product
    open_roles   TEXT,          -- JSON array of role strings
    source       TEXT DEFAULT 'claude_search',
    created_at   TEXT DEFAULT (datetime('now'))
);

-- Recruiter and hiring manager contacts
CREATE TABLE contacts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER REFERENCES companies(id),
    name         TEXT NOT NULL,
    title        TEXT,
    email        TEXT,
    linkedin_url TEXT,
    source       TEXT NOT NULL, -- 'ai' | 'manual'
    status       TEXT DEFAULT 'Not Contacted',
                 -- 'Not Contacted' | 'Drafted' | 'Sent' | 'Replied'
                 -- | 'Interview' | 'Rejected'
    notes        TEXT,
    created_at   TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now'))
);

-- Email drafts and their send state
CREATE TABLE emails (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id   INTEGER REFERENCES contacts(id),
    email_type   TEXT NOT NULL, -- 'internship' | 'full-time' | 'networking' | 'follow-up'
    subject      TEXT,
    body         TEXT NOT NULL,
    status       TEXT DEFAULT 'drafted', -- 'drafted' | 'sent' | 'failed'
    gmail_message_id TEXT,      -- returned by Gmail MCP after send
    drafted_at   TEXT DEFAULT (datetime('now')),
    sent_at      TEXT
);

-- User profile / settings (single-row table, id always = 1)
CREATE TABLE settings (
    id           INTEGER PRIMARY KEY DEFAULT 1,
    full_name    TEXT,
    degree       TEXT DEFAULT 'MS Data Science',
    university   TEXT DEFAULT 'University of Maryland',
    gpa          TEXT DEFAULT '4.0',
    years_exp    INTEGER DEFAULT 4,
    current_role TEXT,          -- e.g. 'Teaching Assistant'
    focus_areas  TEXT,          -- e.g. 'ML, NLP'
    resume_text  TEXT,          -- full resume paste for prompt context
    updated_at   TEXT DEFAULT (datetime('now'))
);
```

### Key relationships

- `companies` 1→N `contacts`
- `contacts` 1→N `emails` (user may send follow-ups; each is its own row)
- `settings` is effectively a singleton config row

### Indexes to add at phase 1

```sql
CREATE INDEX idx_contacts_company ON contacts(company_id);
CREATE INDEX idx_contacts_status  ON contacts(status);
CREATE INDEX idx_emails_contact   ON emails(contact_id);
CREATE INDEX idx_emails_status    ON emails(status);
```

---

## Multi-Page Navigation Pattern

Streamlit's native multi-page structure (introduced in 1.10, stable by 1.20+) uses a `pages/` directory. Each file in `pages/` becomes a sidebar nav item automatically.

**Recommended file layout:**

```
outreach/
├── app.py                  # Entry point — sets page config, initializes DB
├── db.py                   # SQLite connection + all CRUD functions
├── pages/
│   ├── 1_Discover.py
│   ├── 2_Contacts.py
│   ├── 3_Email_Drafting.py
│   ├── 4_Tracker.py
│   ├── 5_Dashboard.py
│   └── 6_Settings.py
├── services/
│   ├── claude.py
│   ├── contacts.py
│   ├── discovery.py
│   ├── email_service.py
│   ├── export.py
│   ├── gmail_mcp.py
│   └── tracker.py
└── utils/
    ├── state.py            # session_state key constants + typed helpers
    └── settings.py         # profile read/write helpers
```

`app.py` calls `db.py`'s `init_db()` on startup so tables exist before any page loads. Because Streamlit re-runs the active page script on every user interaction, `init_db()` must be idempotent (`CREATE TABLE IF NOT EXISTS`).

---

## Session State Management for Multi-Step Workflows

Streamlit reruns the entire page script on every widget interaction. Session state (`st.session_state`) is the only persistent store between reruns within a session.

### Workflow step pattern

Define an enum (or string constants) for each workflow's steps and store the current step in session state:

```python
# utils/state.py
DISCOVER_STEP = "discover_step"      # 'filters' | 'results' | 'saved'
DRAFT_STEP    = "draft_step"         # 'select_contact' | 'select_type' | 'review' | 'sent'
SELECTED_COMPANY   = "selected_company_id"
SELECTED_CONTACT   = "selected_contact_id"
CURRENT_DRAFT      = "current_draft_body"
CURRENT_DRAFT_ID   = "current_draft_email_id"
DISCOVERY_RESULTS  = "discovery_results"   # list[dict], ephemeral
```

Pages read the step key to decide which sub-view to render, and advance it on button clicks. This avoids complex conditional nesting and makes the workflow state inspectable.

### Cross-page state

When a user clicks "Draft email" from the Contacts page, store the `contact_id` in session state and `st.switch_page("pages/3_Email_Drafting.py")`. The Email Drafting page reads `st.session_state[SELECTED_CONTACT]` on load to pre-populate the contact selector. This is the correct Streamlit pattern for cross-page data passing — do not use query params or URL state for local apps.

---

## Handling Long-Running Anthropic API Calls Without Blocking the UI

**Confidence: HIGH** — this is well-established Streamlit community practice.

### The problem

Streamlit is single-threaded per session. A blocking `client.messages.create()` call (which can take 5-30 seconds for web_search) freezes the entire UI — the spinner stops updating, the user cannot cancel, and Streamlit may show a timeout warning.

### Solution: `st.status` + streaming

The Anthropic Python SDK supports streaming responses. Use `client.messages.stream()` as a context manager and write tokens into an `st.empty()` placeholder as they arrive. This gives immediate feedback and keeps Streamlit's event loop responsive between token writes.

```python
# services/claude.py  (illustrative — not production code)
import anthropic

def stream_email_draft(prompt: str, profile: dict) -> str:
    client = anthropic.Anthropic()
    full_text = []
    with client.messages.stream(
        model="claude-opus-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text_chunk in stream.text_stream:
            full_text.append(text_chunk)
            yield text_chunk          # caller writes each chunk to st.empty()
    return "".join(full_text)
```

In the page:

```python
# pages/3_Email_Drafting.py  (illustrative)
placeholder = st.empty()
accumulated = []
with st.status("Drafting email with Claude..."):
    for chunk in email_service.stream_draft(contact, email_type, profile):
        accumulated.append(chunk)
        placeholder.markdown("".join(accumulated))
draft_body = "".join(accumulated)
```

### Solution for web_search (discovery calls)

The Anthropic web_search tool does not stream incrementally — the model searches, then responds. For discovery calls use `st.status()` with an indeterminate spinner to signal work is in progress, and do the call synchronously inside it. Typical latency is 8-20 seconds; the spinner keeps UI from looking frozen.

```python
with st.status("Searching for companies...", expanded=True) as status_widget:
    status_widget.write("Claude is scanning the web for AI/ML startups...")
    companies = discovery.run_search(filters)   # blocking call, but spinner shows
    status_widget.write(f"Found {len(companies)} companies.")
status_widget.update(label="Search complete", state="complete")
```

### What NOT to do

- Do not use `threading.Thread` to run Anthropic calls in background threads and poll from the UI — Streamlit's session state is not thread-safe and this causes race conditions and unpredictable reruns.
- Do not use `asyncio.run()` inside a Streamlit callback — Streamlit runs in its own event loop context; nested `asyncio.run()` raises `RuntimeError: This event loop is already running`.
- Do not cache Anthropic calls with `@st.cache_data` — responses are unique per call and caching will serve stale drafts.

---

## Suggested Build Order

The dependency graph drives this order. Each phase produces working, runnable software.

### Phase 1 — Data Foundation

Build first because everything else depends on it.

1. `db.py` — `init_db()` with all four tables, idempotent schema creation
2. `app.py` — page config, call `init_db()` on startup
3. `utils/state.py` — session state key constants
4. `pages/6_Settings.py` — profile entry form; writes to `settings` table. Build early so drafting has real context from the start.
5. Verify: run `streamlit run app.py`, navigate to Settings, save profile, confirm DB row exists.

### Phase 2 — Discovery Pipeline (Highest Value, Week 1)

1. `services/claude.py` — Anthropic client wrapper, `call_with_web_search()`, streaming helper
2. `services/discovery.py` — prompt builder, response parser, save to `companies`
3. `pages/1_Discover.py` — filter form, `st.status()` spinner, company result cards, "Save" button

### Phase 3 — Contacts

1. `services/contacts.py` — contact CRUD, source badge logic
2. `pages/2_Contacts.py` — contact list per company, manual add form, source badge display

### Phase 4 — Email Drafting + Sending

Contacts must exist before drafting; Gmail MCP must be configured before sending.

1. `services/gmail_mcp.py` — MCP client invocation wrapper, error surface
2. `services/email_service.py` — draft prompt builder, `stream_draft()`, send orchestration
3. `pages/3_Email_Drafting.py` — contact selector, type selector, streaming draft display, send button

### Phase 5 — Tracker

Tracker is read-heavy; sending must work first so there is data to track.

1. `services/tracker.py` — status transition logic, notes update
2. `pages/4_Tracker.py` — joined DataFrame, color-coded status badges, inline edit widgets

### Phase 6 — Dashboard + Export

Requires all prior data to be meaningful.

1. `services/export.py` — DataFrame builder, CSV serialization
2. `pages/5_Dashboard.py` — `st.metric` cards, filter widgets, `st.download_button`

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: DB calls inside widget callbacks
**What happens:** `on_change` callbacks run during Streamlit's diff phase; DB errors there produce cryptic tracebacks.
**Instead:** Set a session state flag in the callback, then check and execute the DB call in the main page body on the next rerun.

### Anti-Pattern 2: Opening a new sqlite3 connection per function call
**What happens:** SQLite allows multiple connections, but WAL mode is not enabled by default; concurrent writes from rapid reruns can cause `database is locked` errors.
**Instead:** Use a module-level connection or a context manager that opens/closes within a single service call. Enable WAL mode at startup: `PRAGMA journal_mode=WAL`.

### Anti-Pattern 3: Storing large DataFrames in session state
**What happens:** Session state is in-memory per session; caching a 10K-row DataFrame there bloats memory and slows reruns.
**Instead:** Store only the filter parameters in session state and re-query the DB on each rerun. SQLite queries on a local file are fast enough (< 50ms for thousands of rows).

### Anti-Pattern 4: One giant monolithic page file
**What happens:** 600-line page files become unmaintainable quickly; Streamlit reruns the entire file on every interaction.
**Instead:** Extract logical sections into functions within the page file (e.g., `render_filter_form()`, `render_results_grid()`). Keep the main body of the page file under 50 lines.

### Anti-Pattern 5: Hardcoding the Claude model name in multiple places
**What happens:** When you upgrade from `claude-opus-4-5` to a newer model, you change it in three files and miss one.
**Instead:** Define `CLAUDE_MODEL = "claude-opus-4-5"` once in `services/claude.py` (or a `config.py`) and import it everywhere.

---

## Scalability Considerations

This is a local single-user app; "scalability" here means graceful degradation as the contact list grows over months of active outreach.

| Concern | At 100 contacts | At 1,000 contacts | At 5,000 contacts |
|---------|----------------|-------------------|-------------------|
| Tracker query speed | Instant | < 50ms with indexes | < 200ms with indexes |
| Dashboard aggregation | Instant | Instant | Use `GROUP BY` SQL, not pandas groupby |
| Discovery result storage | Fine | Fine | Add pagination to result cards |
| Session state bloat | None | None | Never store full result sets in state |
| SQLite file size | < 1MB | < 10MB | < 50MB — still fine locally |

SQLite with WAL mode and the four indexes defined above will handle this app's full lifetime without any schema changes.

---

## Gmail MCP Integration Topology

**Confidence: MEDIUM** — Gmail MCP is less standardized than the rest of this stack. The pattern below reflects how MCP tool clients work generically; verify against the specific Gmail MCP server's invocation contract.

The Gmail MCP server runs as a local process (likely Node.js or Python) that Streamlit communicates with over stdio or a local socket. The `services/gmail_mcp.py` wrapper should:

1. Accept `(to: str, subject: str, body: str)` and return `(success: bool, message_id: str | None, error: str | None)`.
2. Keep MCP invocation details (process management, protocol framing) fully encapsulated — the email service never knows it's talking to MCP.
3. Surface send failures as explicit return values, not exceptions, so the UI can show a clear error without a full page crash.

If the Gmail MCP server requires a running process to be started before Streamlit, document that in the project README and consider auto-starting it from `app.py` using `subprocess.Popen` with a startup check.

---

## Sources

- Streamlit multi-page app documentation: stable API since Streamlit 1.10 (HIGH confidence — core framework feature)
- Anthropic Python SDK streaming API: `client.messages.stream()` context manager pattern (HIGH confidence — SDK is well-documented)
- SQLite WAL mode and connection patterns: standard SQLite documentation (HIGH confidence)
- Gmail MCP integration topology: inferred from general MCP client patterns (MEDIUM confidence — verify against actual Gmail MCP server docs)
- Session state multi-step workflow pattern: established Streamlit community practice (HIGH confidence)

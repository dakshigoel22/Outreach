# Technology Stack

**Project:** Recruiter Outreach CRM
**Researched:** 2026-05-24
**Research mode:** Ecosystem (Stack dimension only)
**Tool availability:** All external lookup tools (Bash, WebSearch, WebFetch, Context7) blocked in this environment. All findings drawn from training knowledge (cutoff August 2025). Confidence levels reflect this limitation — verify versions before coding.

---

## Recommended Stack

### Core Framework

| Technology | Version (verify) | Purpose | Why |
|------------|-----------------|---------|-----|
| Python | 3.11+ | Runtime | 3.11 brings meaningful perf gains over 3.10; 3.12 is stable but some ML deps lag; 3.11 is the safe current sweet spot. |
| Streamlit | 1.35+ | UI layer | Purpose-built for data apps; `st.data_editor` (stable since 1.23) covers inline CRM editing without custom JS; multipage via `pages/` directory is first-class. |
| Anthropic Python SDK | 0.28+ | Claude API client | Official SDK; provides typed client, streaming, tool_use block handling, and the `web_search` tool integration point. |
| SQLite (stdlib) | 3.x (bundled) | Persistence | Zero-config, file-based, ships with Python. Right-sized for a single-user local app with a few thousand rows. |
| pandas | 2.1+ | Data manipulation | Required by `st.data_editor`; 2.x uses Copy-on-Write by default which avoids silent mutation bugs common in 1.x. |

**Confidence:** MEDIUM — Streamlit and Anthropic SDK minor versions should be verified at `pip install` time; major API shape is stable.

---

### Database Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| sqlite3 (stdlib) | bundled | DB driver | No install needed; works fine for all CRUD at this scale. |
| SQLAlchemy Core (optional) | 2.0+ | Connection management | If you hit Streamlit thread-safety issues (see Pitfalls), `SQLAlchemy` with `StaticPool` or `NullPool` solves them cleanly. Do NOT use the ORM — Core + raw SQL is lighter and keeps pandas integration simple. |

**Recommendation:** Start with raw `sqlite3`. Add SQLAlchemy only if you observe "database is locked" or "ProgrammingError: Cannot operate on a closed database" errors under Streamlit reruns.

**Confidence:** HIGH — This is well-established for Streamlit + SQLite apps.

---

### AI Integration

| Technology | Version (verify) | Purpose | Why |
|------------|-----------------|---------|-----|
| anthropic | 0.28+ | Claude API calls | Official client; the only supported way to call Anthropic APIs. |

**Anthropic SDK `web_search` tool — current API shape (as of training cutoff):**

The `web_search` tool is a **built-in Anthropic tool**, not a user-defined function. You pass it in the `tools` list as a named tool reference; Anthropic's servers execute the search and return results as `tool_result` blocks. The model handles when to call it.

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-5",          # or claude-sonnet-4-5; verify current names
    max_tokens=4096,
    tools=[
        {
            "type": "web_search_20250305",   # tool type string — verify exact value in docs
            "name": "web_search",
        }
    ],
    messages=[
        {
            "role": "user",
            "content": "Find AI/ML startups in NYC that are Series A, 10-50 employees, with an active ML product. Return company name, funding stage, headcount, and website."
        }
    ]
)
```

**Model support:** The `web_search` tool is supported on Claude 3.5 Sonnet, Claude 3.5 Haiku, and Claude 3 Opus class models. As of mid-2025, `claude-sonnet-4-5` and `claude-opus-4-5` are the current production names — verify at `https://docs.anthropic.com/en/docs/about-claude/models`.

**Tool type string:** The exact `type` value (e.g., `"web_search_20250305"`) is versioned and subject to change. Always pull the current value from the Anthropic docs page on built-in tools before implementation.

**Agentic loop:** For discovery workflows where Claude may call web_search multiple times, you must implement an agentic loop:

```python
messages = [{"role": "user", "content": user_prompt}]

while True:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=messages,
    )

    if response.stop_reason == "end_turn":
        break

    if response.stop_reason == "tool_use":
        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})
        # Build tool_result blocks for each tool_use block
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                # For built-in tools, Anthropic handles execution —
                # the result comes back in the NEXT response automatically.
                # This loop structure is for user-defined tools.
                # For web_search (built-in), stop_reason is "end_turn" after search.
                pass
        break
```

**Important nuance:** For Anthropic's built-in `web_search` tool, the model executes the search server-side and returns results inline — you do NOT receive a `tool_use` stop with a block you need to resolve yourself (unlike user-defined tools). The response comes back as `end_turn` with the synthesized answer. The agentic loop pattern above is needed if you layer additional user-defined tools alongside web_search.

**Confidence:** MEDIUM — The general shape is correct per training knowledge. The exact `type` string and whether built-in tools surface `tool_use` stop reasons must be verified against current Anthropic docs before coding. This is the most important verification step in the entire stack.

---

### Email Integration

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Gmail MCP server | community | Email sending | User-mandated; keeps sending in-app without SMTP complexity. |

**Gmail MCP — how it works:**

MCP (Model Context Protocol) is Anthropic's open protocol for giving Claude access to external tools and data sources. A Gmail MCP server exposes Gmail capabilities (send, read, list) as MCP tools that Claude can call.

**Credential requirements:**
- Google OAuth 2.0 credentials (client ID + client secret from Google Cloud Console)
- A `credentials.json` file downloaded from your GCP project
- First-run browser OAuth flow to generate `token.json` (refresh token persists locally)
- Gmail API must be enabled in the GCP project

**Integration pattern in this app:**
The Gmail MCP server runs as a local subprocess (stdio transport). Your Streamlit app communicates with it via the `mcp` Python client library, which surfaces the `send_email` tool to Claude. The send flow is:

1. User reviews draft in Streamlit UI
2. User clicks "Send"
3. App calls MCP client → Gmail MCP server → Gmail API
4. Status returned to UI

**Current limitation — CRITICAL:** In Streamlit apps, the MCP client connection lifecycle is non-trivial. MCP servers typically expect a persistent stdio connection, but Streamlit reruns the entire script on each interaction. You must manage the MCP client as a singleton (via `st.session_state` or a module-level singleton) to avoid spawning a new subprocess on every rerun. If done wrong, you'll accumulate zombie subprocesses.

**Which Gmail MCP server to use:** As of training cutoff, the primary options are:
- `@modelcontextprotocol/server-gmail` (Node.js, from the official MCP examples repo) — requires Node.js runtime alongside Python
- Community Python ports exist but are less mature

**Recommendation:** Use the official Node.js Gmail MCP server. Add Node.js as a dev dependency (via `nvm` or system install). The `mcp` Python package (`pip install mcp`) provides the client-side Python SDK to talk to it.

**Confidence:** LOW-MEDIUM — Gmail MCP integration with Streamlit is a non-standard combination. The credential flow is well-understood (standard OAuth2); the Streamlit subprocess lifecycle management is the risky part and requires careful implementation. Verify the current `mcp` Python package API before coding.

---

### Supporting Libraries

| Library | Version (verify) | Purpose | When to Use |
|---------|-----------------|---------|-------------|
| `st-aggrid` | 0.3.x | Advanced data grid | If `st.data_editor` proves insufficient (complex column types, row grouping). Heavy JS dependency — prefer native `st.data_editor` first and only add this if blocked. |
| `pydantic` | 2.x | Data validation | Validate Claude's JSON output before writing to SQLite. Claude web_search responses are unstructured; always parse/validate before persistence. |
| `python-dotenv` | 1.0+ | Env var management | Store `ANTHROPIC_API_KEY` in `.env`; never hardcode. |
| `tenacity` | 8.x | Retry logic | Wrap Anthropic API calls with exponential backoff; web_search calls can hit rate limits. |
| `httpx` | 0.27+ | HTTP client | Anthropic SDK dependency; do not install separately unless needed for direct requests. |

**Do NOT use:**
- `streamlit-aggrid` unless `st.data_editor` is genuinely insufficient — it adds a JS build dependency and breaks on Streamlit version updates frequently.
- `SQLAlchemy ORM` — heavy abstraction unnecessary for this app; Core or raw sqlite3 is enough.
- `aiosqlite` — async SQLite driver; not needed since Streamlit runs synchronously per rerun.
- Any additional AI API clients (OpenAI, etc.) — project constraint is Anthropic-only.

**Confidence:** HIGH for python-dotenv, pydantic, tenacity. MEDIUM for st-aggrid (version compatibility is historically fragile).

---

## Streamlit Patterns for a Data-Dense CRM

### Multi-page Architecture

Use the `pages/` directory convention (stable since Streamlit 1.10):

```
app.py               # Entry point, shared sidebar nav
pages/
  1_Discover.py      # Claude web_search trigger + results table
  2_Contacts.py      # Full contact tracker with st.data_editor
  3_Draft_Email.py   # Contact selector + email type + Claude draft
  4_Dashboard.py     # Summary cards + filterable table + CSV export
  5_My_Profile.py    # User background settings form
```

The `1_` prefix controls sidebar ordering. `st.session_state` persists across pages within a session.

### Inline Editing with `st.data_editor`

`st.data_editor` is the right primitive for the tracker table. Key patterns:

```python
import streamlit as st
import pandas as pd

# Load from SQLite
df = load_contacts_from_db()

# Render editable table
edited_df = st.data_editor(
    df,
    column_config={
        "status": st.column_config.SelectboxColumn(
            "Status",
            options=["Not Contacted", "Drafted", "Sent", "Replied", "Interview", "Rejected"],
            required=True,
        ),
        "notes": st.column_config.TextColumn("Notes", width="large"),
        "email": st.column_config.LinkColumn("Email"),
        "source": st.column_config.SelectboxColumn(
            "Source",
            options=["AI-discovered", "Manual"],
        ),
    },
    hide_index=True,
    num_rows="fixed",   # "dynamic" allows row add/delete; use "fixed" for tracker
    use_container_width=True,
)

# Detect changes and persist
if not df.equals(edited_df):
    save_changes_to_db(edited_df)
    st.success("Saved")
```

**Important:** `st.data_editor` returns the full edited dataframe on every rerun. Use `df.equals(edited_df)` before writing to SQLite to avoid spurious writes.

### Session State for CRUD

```python
# Initialize once
if "selected_contact_id" not in st.session_state:
    st.session_state.selected_contact_id = None

if "draft_text" not in st.session_state:
    st.session_state.draft_text = ""
```

Keep IDs (not full row objects) in `st.session_state`. Reload the full row from SQLite when needed — avoids stale state bugs.

### Status Badges (Color-Coded)

Streamlit does not natively render colored badges in tables. Two approaches:

1. **`st.data_editor` SelectboxColumn** (recommended): Status is a dropdown; no color coding in table, but functional.
2. **`st.markdown` with HTML** for detail views: `st.markdown(':green[Replied]', unsafe_allow_html=False)` — use Streamlit's colored text rather than raw HTML injection.

Full CSS-styled badge columns require `unsafe_allow_html=True` in a `st.markdown` block or `st.write`, which is acceptable for local-only apps but avoid in any hosted context.

**Confidence:** HIGH for `st.data_editor` patterns (stable, well-documented). MEDIUM for badge styling (workaround territory).

---

## SQLite + pandas Thread Safety in Streamlit

**The core issue:** Streamlit runs each user interaction as a Python script rerun, potentially across different threads (especially with multiple browser tabs). SQLite's default `check_same_thread=True` will raise errors if a connection created in one thread is used in another.

**Recommended pattern:**

```python
import sqlite3
import streamlit as st

@st.cache_resource
def get_db_connection():
    """Create one connection per app lifetime, shared across reruns."""
    conn = sqlite3.connect(
        "outreach.db",
        check_same_thread=False,   # Required for Streamlit
    )
    conn.row_factory = sqlite3.Row  # Enables dict-like row access
    return conn
```

**Why `@st.cache_resource`:** It creates a singleton that persists for the app's lifetime, not just one rerun. This is Streamlit's recommended pattern for database connections.

**Why `check_same_thread=False`:** Streamlit's threading model means the same connection object may be accessed from different threads. SQLite's write lock (one writer at a time) still protects against corruption; `check_same_thread=False` just disables the overly conservative Python-level thread check.

**Write safety:** Always use context managers for writes:

```python
conn = get_db_connection()
with conn:   # auto-commits on success, rolls back on exception
    conn.execute("INSERT INTO contacts (...) VALUES (...)", params)
```

**pandas read pattern:**

```python
import pandas as pd

def load_contacts() -> pd.DataFrame:
    conn = get_db_connection()
    return pd.read_sql_query(
        "SELECT * FROM contacts ORDER BY created_at DESC",
        conn
    )
```

**Do NOT use:** `pandas.DataFrame.to_sql` with `if_exists="replace"` for updates — it drops and recreates the table, destroying any rows not in the current DataFrame. Use explicit `UPDATE` statements.

**Confidence:** HIGH — `@st.cache_resource` + `check_same_thread=False` is the documented Streamlit pattern for SQLite.

---

## Schema Design (Starter)

```sql
CREATE TABLE IF NOT EXISTS contacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company     TEXT NOT NULL,
    name        TEXT NOT NULL,
    title       TEXT,
    email       TEXT,
    linkedin    TEXT,
    source      TEXT NOT NULL CHECK(source IN ('ai', 'manual')),
    status      TEXT NOT NULL DEFAULT 'Not Contacted'
                    CHECK(status IN ('Not Contacted','Drafted','Sent','Replied','Interview','Rejected')),
    notes       TEXT,
    draft_text  TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS companies (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    tier          TEXT CHECK(tier IN ('2','3')),
    funding_stage TEXT,
    headcount     TEXT,
    location      TEXT,
    website       TEXT,
    ai_product    TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_profile (
    id          INTEGER PRIMARY KEY CHECK(id = 1),  -- enforce single row
    full_name   TEXT,
    degree      TEXT,
    gpa         TEXT,
    years_exp   INTEGER,
    roles       TEXT,   -- JSON array of target roles
    resume_text TEXT,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Confidence:** HIGH — Schema is derived directly from project requirements; no external verification needed.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| UI framework | Streamlit | Dash (Plotly) | Dash requires more boilerplate for simple CRUD; Streamlit is faster for data-dense local apps |
| UI framework | Streamlit | FastAPI + React | Massive overkill for single-user local app; no browser state needed |
| DB driver | sqlite3 + st.cache_resource | SQLAlchemy ORM | ORM adds abstraction with no benefit at this scale; raw SQL + pandas is simpler |
| Data grid | st.data_editor | st-aggrid | st-aggrid has JS dependency and version fragility; st.data_editor is sufficient for this use case |
| Email delivery | Gmail MCP | smtplib / sendgrid | Project constraint; MCP keeps sending in-app and is user-mandated |
| AI SDK | anthropic | openai / litellm | Project constraint; Anthropic SDK is the only supported client |
| Retry logic | tenacity | manual retry loops | tenacity provides exponential backoff, jitter, and decorators in 3 lines |

---

## Installation

```bash
# Core app
pip install streamlit>=1.35 anthropic>=0.28 pandas>=2.1 pydantic>=2.0 python-dotenv>=1.0 tenacity>=8.0

# MCP client for Gmail integration
pip install mcp

# Optional: only add if st.data_editor is insufficient
# pip install streamlit-aggrid
```

**Node.js requirement for Gmail MCP server:**
```bash
# Install Node.js (via nvm recommended)
nvm install --lts
# Install the Gmail MCP server
npx @modelcontextprotocol/server-gmail
```

**Environment file (`.env` — never commit):**
```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Version Verification Checklist

Before writing any code, verify these at the official sources:

| Item | Where to verify | Why critical |
|------|----------------|--------------|
| Anthropic `web_search` tool type string | `https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search-tool` | Type string is versioned and changes |
| Current Claude model names | `https://docs.anthropic.com/en/docs/about-claude/models` | Model IDs change with new releases |
| Streamlit `st.data_editor` column config API | `https://docs.streamlit.io/develop/api-reference/data/st.data_editor` | Column config options evolve |
| `mcp` Python package API | `https://pypi.org/project/mcp/` | Package is relatively new; API may have changed |
| Gmail MCP server package name | `https://github.com/modelcontextprotocol/servers` | Package name and install method may differ |

---

## Sources

All findings from training knowledge (cutoff August 2025). External lookup tools (WebSearch, WebFetch, Bash/Context7 CLI) were blocked in this research environment.

Official sources to consult before coding:
- Anthropic SDK docs: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search-tool
- Anthropic model list: https://docs.anthropic.com/en/docs/about-claude/models
- Streamlit data_editor: https://docs.streamlit.io/develop/api-reference/data/st.data_editor
- Streamlit multipage: https://docs.streamlit.io/develop/concepts/multipage-apps
- Streamlit cache_resource: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- MCP server registry: https://github.com/modelcontextprotocol/servers

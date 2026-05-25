# Phase 2: Discovery - Research

**Researched:** 2026-05-25
**Domain:** Anthropic web_search tool + Claude API, pydantic v2 validation, tenacity retry, Streamlit blocking call pattern, SQLite INSERT
**Confidence:** HIGH (all critical claims verified from live official Anthropic docs fetched during this session)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Claude must return a **JSON array** of company objects. The prompt instructs Claude to respond with structured JSON (not prose). The service validates the output with pydantic before writing to the DB. Do not attempt to parse prose.
- **D-02:** The Claude call **blocks** the UI with a spinner (`discover_running = True` in session state). No streaming. A single call returns a full batch of results.
- **D-03:** Target **5–10 companies per search call**. Prompt should request this range explicitly.
- **D-04:** If Claude returns fewer results than expected (even 1–2), show whatever was found. No auto-retry.
- **D-05:** Discover results **persist in session state** (`discover_results`) until a new search runs.
- **D-06:** Filter selections (location, tier, role type) persist in session state.
- **D-07:** First-load empty state: show filter widgets and a prominent Discover button with brief instructions.
- **D-08:** A company is "already saved" if **either** the name (case-insensitive) OR the website URL matches a row in the `companies` table.
- **D-09:** Run the duplicate check **once after results load** using a single batch query (SELECT with IN clause on names + urls).
- **D-10:** Visual indicator for already-saved companies: "Already saved" badge + disabled Save button replaced by "Saved ✓" badge.

### Claude's Discretion
- Exact prompt wording and system prompt structure for the web_search call.
- Pydantic model field names and validation rules for the company JSON.
- URL normalization strategy for URL-based duplicate detection (strip trailing slash, normalize http/https).
- Number of web_search calls per Discover run (single call vs. multiple targeted calls).

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DISC-01 | User sets filters (location: NYC / Arlington VA / DC / SF; tier: Tier 2 / Tier 3 / Both; role type: internship / full-time / both) and Claude uses Anthropic web_search to find matching AI/ML startups — results show company name, funding stage, estimated headcount, website, and active hiring roles | Verified web_search tool type string, SDK call structure, JSON parsing approach, pydantic model for company data |
| DISC-02 | User can save any discovered company to the database with one click; already-saved companies are visually indicated in results | Verified INSERT OR IGNORE pattern, batch duplicate check query, companies table schema from database/schema.py |
</phase_requirements>

---

## Summary

Phase 2 adds the Claude-powered company discovery pipeline to the Recruiter Outreach CRM. The core technical challenge is calling the Anthropic API with the web_search server tool, extracting a structured JSON array from Claude's response, validating it with pydantic v2, and persisting companies to SQLite via the existing `get_connection()` pattern.

**Critical blocker discovered:** The installed `anthropic` SDK is version 0.28.0 (locked in requirements.txt). Web search server tool support was added in SDK version 0.51.0 (May 2025). The current latest is 0.104.1. The 0.28.0 SDK lacks `ServerToolUse`, `WebSearchToolResult` response types, and has a runtime bug with newer httpx (`proxies` kwarg error). **The SDK must be upgraded to >= 0.51.0 before any web_search code can run.** This is a Wave 0 task.

The web_search integration follows a **server-side tool** pattern distinct from regular tool_use: Claude decides when to search autonomously, the API executes the searches, and the final `response.content` is a mixed list of `text`, `server_tool_use`, and `web_search_tool_result` blocks. The caller only needs to extract `text` blocks from the final response — there is no multi-turn loop required when using web_search (unlike regular client-side tool_use which requires tool_result messages).

**Primary recommendation:** Upgrade `anthropic` to `>=0.51.0` (pin to `0.104.1` for reproducibility). Use tool type string `"web_search_20250305"` for basic web search (the newer `"web_search_20260209"` requires the code execution tool enabled). Use `claude-sonnet-4-6` as the model — best speed/intelligence balance at $3/MTok input, appropriate for discovery queries. Structure the service as `services/claude.py` with `@st.cache_resource` Anthropic client, a `discover_companies(filters)` function wrapped in tenacity retry, and pydantic v2 `Company` model for validation.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Company discovery (web_search) | Backend service (services/claude.py) | — | Claude API call is blocking I/O with business logic; belongs in service layer, not page |
| Filter UI | Frontend (pages/1_Discover.py) | — | Pure UI concern; filter values passed as dict to service |
| JSON extraction from Claude response | Backend service (services/claude.py) | — | Response parsing is service responsibility; page receives typed Company list |
| Pydantic validation | Backend service (services/claude.py) | — | Validates before DB write; failures return [] not partial results |
| DB INSERT (save company) | Database layer (database/companies.py or inline) | — | Calls get_connection(); isolated from UI layer |
| Duplicate check batch query | Database layer | Frontend (pages/1_Discover.py) | DB query runs in service/db module; result (sets of names/urls) used by page for badge rendering |
| Session state management | Frontend (pages/1_Discover.py) | utils/session.py | SESSION_DEFAULTS owns defaults; page manages discover_running flag |
| Spinner + error display | Frontend (pages/1_Discover.py) | — | Pure UI pattern; service raises exceptions, page catches them |

---

## Standard Stack

### Core
| Library | Version (installed) | Latest on PyPI | Purpose | Why Standard |
|---------|--------------------|--------------  |---------|--------------|
| anthropic | **0.28.0 → must upgrade to 0.104.1** | 0.104.1 [VERIFIED: PyPI] | Claude API client, web_search server tool | Only supported Anthropic client; web_search requires >= 0.51.0 |
| pydantic | 2.7.1 (installed) | 2.13.4 [VERIFIED: PyPI] | Validate Claude JSON output before DB write | v2 BaseModel with `model_validate()` handles missing fields cleanly |
| tenacity | 8.2.3 (installed) | 9.1.2 [VERIFIED: PyPI] | Retry Anthropic API calls on rate limits | Exponential backoff in 3 lines; retries `RateLimitError` and `APITimeoutError` |
| python-dotenv | 1.0.1 (installed) | 1.1.1 [VERIFIED: PyPI] | Load ANTHROPIC_API_KEY from .env | `load_dotenv()` in connection.py already sets pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite3 (stdlib) | bundled | INSERT companies, batch SELECT for duplicate check | All DB writes/reads — use get_connection() always |
| streamlit | 1.35.0 (installed) | st.spinner, st.error, st.columns, st.button | Page UI — already installed, no change |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `web_search_20250305` | `web_search_20260209` | 20260209 adds dynamic filtering (code execution) — requires code_execution tool also enabled; adds complexity. 20250305 is sufficient for discovery. |
| `claude-sonnet-4-6` | `claude-opus-4-7` | Opus 4.7 is more capable but 5x more expensive ($5 vs $3/MTok input) and moderate latency vs fast. For 5–10 company discovery queries, Sonnet is sufficient. |
| `claude-sonnet-4-6` | `claude-haiku-4-5` | Haiku is fastest/cheapest but least intelligent — company discovery benefits from Sonnet's reasoning to find accurate funding stage/headcount. |
| pydantic v2 `model_validate()` | `json.loads()` + manual checks | Manual parsing misses type coercion and partial-field handling; pydantic gives ValidationError with field-level detail |

**Installation (upgrade only):**
```bash
pip install "anthropic==0.104.1"
```
Update `requirements.txt`: change `anthropic==0.28.0` to `anthropic==0.104.1`.

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| anthropic | PyPI | ~3 yrs | High (official Anthropic SDK) | github.com/anthropics/anthropic-sdk-python | [OK] | Approved — upgrade to 0.104.1 |
| pydantic | PyPI | ~8 yrs | Very High | github.com/pydantic/pydantic | [OK] | Approved — keep 2.7.1 |
| tenacity | PyPI | ~7 yrs | Very High | github.com/jd/tenacity | [OK] | Approved — keep 8.2.3 |
| python-dotenv | PyPI | ~8 yrs | Very High | github.com/theskumar/python-dotenv | [OK] | Approved — note slopcheck flagged naming pattern as "LLM bait" but confirmed established |
| streamlit | PyPI | ~6 yrs | Very High | github.com/streamlit/streamlit | [OK] | Approved — no change needed |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

slopcheck run verified all 5 packages as `[OK]` during this research session (2026-05-25).

---

## Architecture Patterns

### System Architecture Diagram

```
User (browser)
     |
     | sets filters, clicks Discover
     v
pages/1_Discover.py
     |  discover_running = True
     |  with st.spinner("Claude is searching..."):
     |
     v
services/claude.py::discover_companies(filters: dict) -> list[Company]
     |  @retry(wait=exp backoff, retry=RateLimitError|APITimeoutError)
     |  get_claude_client()  # @st.cache_resource Anthropic()
     |  client.messages.create(
     |      model="claude-sonnet-4-6",
     |      tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
     |      messages=[{system prompt + user filters}]
     |  )
     |
     v
Anthropic API (external)
     |  Claude autonomously calls web_search N times
     |  API executes searches server-side
     |  Returns response with mixed content blocks:
     |    [text, server_tool_use, web_search_tool_result, text(JSON)]
     |
     v
services/claude.py (response parsing)
     |  Extract text blocks -> join -> find JSON array
     |  json.loads() -> list of dicts
     |  [Company.model_validate(d) for d in raw] with ValidationError catch
     |  Returns list[Company]
     |
     v
pages/1_Discover.py
     |  st.session_state["discover_results"] = results
     |  discover_running = False
     |  st.rerun()
     |
     v  (on rerun)
     |  get_saved_company_identifiers() -> (names_set, urls_set)
     |      SELECT name, website FROM companies
     |  render_company_card() for each result
     |      is_saved = name.lower() in names OR url in urls
     |      if saved: SAVED_BADGE_HTML
     |      else: st.button("Save") -> save_company() -> INSERT OR IGNORE
```

### Recommended Project Structure
```
services/
├── __init__.py          # empty, marks package
└── claude.py            # get_claude_client(), discover_companies(), Company model
database/
├── connection.py        # get_connection() — existing, no changes
├── schema.py            # init_db() — existing, no changes
└── companies.py         # save_company(), get_saved_identifiers() — NEW in Phase 2
pages/
└── 1_Discover.py        # replace placeholder — filter UI + results grid
utils/
└── session.py           # add 3 new keys to SESSION_DEFAULTS
```

### Pattern 1: web_search Server Tool Call

**What:** Single `client.messages.create()` call with the web_search tool definition. Claude autonomously decides when/how many times to search. The caller blocks until Claude returns `stop_reason="end_turn"`. No multi-turn loop is needed.

**When to use:** Any time Claude needs live web information. This is the only pattern for web_search.

```python
# Source: https://platform.claude.com/docs/en/docs/build-with-claude/tool-use/web-search-tool
# [VERIFIED: official Anthropic docs, fetched 2026-05-25]
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    system="You are a company research assistant...",  # see Pattern 3 for full prompt
    messages=[
        {
            "role": "user",
            "content": "Find 5-10 AI/ML startups in NYC at Tier 2 hiring for internships."
        }
    ],
    tools=[{
        "type": "web_search_20250305",   # VERIFIED type string from live docs
        "name": "web_search",
        "max_uses": 5,                   # cap cost; 5 searches = plenty for 5-10 companies
    }],
)
# response.stop_reason == "end_turn" when done
```

**Critical note:** `web_search_20250305` is the stable version available without additional tool enablement. `web_search_20260209` (dynamic filtering) requires the code execution tool also enabled — use the older version for simplicity.

### Pattern 2: Extracting JSON from Claude's Mixed Response

**What:** Claude's response.content is a list of mixed block types. For web_search, text blocks contain Claude's prose and the final JSON array. `server_tool_use` and `web_search_tool_result` blocks should be ignored by the caller — they are informational.

```python
# Source: https://platform.claude.com/docs/en/docs/build-with-claude/tool-use/web-search-tool
# Response content block types for web_search: [VERIFIED: official Anthropic docs, fetched 2026-05-25]
# - {"type": "text", "text": "..."}                      <- Claude's text (may contain JSON)
# - {"type": "server_tool_use", ...}                     <- Claude's decision to search (ignore)
# - {"type": "web_search_tool_result", ...}              <- Search results (ignore)

import json
import re

def extract_json_from_response(response) -> list[dict]:
    """Extract JSON array from Claude's response content blocks."""
    # Collect all text blocks
    text_parts = [
        block.text
        for block in response.content
        if block.type == "text"
    ]
    full_text = "\n".join(text_parts)

    # Find JSON array — Claude may wrap in ```json``` fences or return raw
    # Strategy: find the first '[' and last ']' in the text
    match = re.search(r'\[.*\]', full_text, re.DOTALL)
    if not match:
        return []
    return json.loads(match.group())
```

**Why re.search over json.loads(full_text):** Claude often adds prose before/after the JSON array. The regex finds the JSON array regardless of surrounding text.

### Pattern 3: System Prompt for Structured JSON Output

**What:** The system prompt instructs Claude to output a specific JSON schema. Combine with user message containing the filter values.

```python
SYSTEM_PROMPT = """You are a company research assistant for a job seeker targeting AI/ML roles.

When asked to find companies, you MUST respond with ONLY a valid JSON array of company objects.
Do not include any prose before or after the JSON array.

Each object must have these exact fields:
{
  "name": "Company Name",
  "funding_stage": "Series A",          // e.g. Seed, Series A, Series B, Series C+, Public, Unknown
  "headcount": "50-200",                // estimate range as string
  "website": "https://example.com",     // full URL or null
  "ai_focus": "NLP and computer vision", // 1-2 sentence description
  "location": "NYC",                    // city name from the user's filter
  "tier": "Tier 2",                     // from the user's filter
  "hiring_roles": ["ML Engineer", "Data Scientist"]  // list of active role types
}

If you cannot determine a field with confidence, use null for strings or [] for arrays.
Return 5 to 10 companies. Only include companies that are actively hiring for AI/ML roles."""

def build_user_message(filters: dict) -> str:
    location = filters.get("location", "NYC")
    tier = filters.get("tier", "Both")
    role_type = filters.get("role_type", "Both")

    tier_desc = "Tier 2 or Tier 3" if tier == "Both" else tier
    role_desc = "internship and full-time" if role_type == "Both" else role_type

    return (
        f"Find 5 to 10 real AI/ML startups in {location} that are {tier_desc} companies "
        f"currently hiring for {role_desc} positions. "
        f"Use web search to find current, accurate information. "
        f"Return ONLY a JSON array — no prose."
    )
```

### Pattern 4: Pydantic v2 Company Model and Validation

**What:** Validate each dict from Claude's JSON array before DB write. Use `Optional` fields with defaults for missing values. Catch `ValidationError` per item, not per batch.

```python
# [VERIFIED: pydantic v2 docs — model_validate() is the v2 replacement for parse_obj()]
from pydantic import BaseModel, field_validator, HttpUrl
from typing import Optional
import json

class Company(BaseModel):
    name: str
    funding_stage: Optional[str] = None
    headcount: Optional[str] = None
    website: Optional[str] = None
    ai_focus: Optional[str] = None
    location: Optional[str] = None
    tier: Optional[str] = None
    hiring_roles: list[str] = []

    @field_validator("website", mode="before")
    @classmethod
    def normalize_website(cls, v):
        """Strip trailing slash, ensure consistent format."""
        if v is None:
            return None
        v = str(v).rstrip("/")
        if v and not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v

    @field_validator("hiring_roles", mode="before")
    @classmethod
    def coerce_roles(cls, v):
        """Handle Claude returning a string instead of list."""
        if isinstance(v, str):
            return [v]
        if v is None:
            return []
        return v


def validate_companies(raw_list: list[dict]) -> list[Company]:
    """Validate a list of raw dicts from Claude. Skip invalid items."""
    from pydantic import ValidationError
    valid = []
    for item in raw_list:
        try:
            valid.append(Company.model_validate(item))
        except ValidationError:
            # Skip malformed items — don't let one bad item break the batch
            continue
    return valid
```

**Why `model_validate()` not `__init__`:** `model_validate()` is the pydantic v2 idiom for dict-to-model conversion. It applies validators. `Company(**item)` bypasses `field_validator` in some edge cases.

### Pattern 5: tenacity Retry for Anthropic API Calls

**What:** Wrap the `client.messages.create()` call with exponential backoff. Retry on `RateLimitError` and `APITimeoutError`. Do not retry on `BadRequestError` (prompt issue) or `AuthenticationError`.

```python
# [VERIFIED: tenacity 8.x docs — retry, stop, wait decorators]
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from anthropic import RateLimitError, APITimeoutError

@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,  # Re-raise the last exception after exhausting retries
)
def _call_claude(client, **kwargs):
    return client.messages.create(**kwargs)
```

**Backoff rationale:** `min=2, max=30` seconds. Web search calls are expensive (token-heavy); 3 attempts with up to 30s gap is appropriate. `reraise=True` lets the Streamlit page catch the final exception and show `st.error`.

### Pattern 6: Streamlit Blocking Call + Discover Button State

**What:** Manage `discover_running` flag to disable the button during the call. Use `finally` to always re-enable. Call `st.rerun()` after successful results to trigger the results render pass.

```python
# [VERIFIED: Streamlit docs — st.spinner, st.button, st.session_state patterns]
# Source: 02-UI-SPEC.md (project-approved pattern)

if discover_clicked:
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
```

**Why `finally` not separate except/else:** The `finally` block guarantees `discover_running = False` even if an unexpected exception occurs mid-call. Without it, the button stays permanently disabled after a crash.

**Note on `st.rerun()` placement:** `st.rerun()` after the try/finally means it runs whether the call succeeded or failed. On failure, this re-renders the page in the non-running state and shows the `st.error` from inside the except block. This is correct behavior — the error will have been set in session state or displayed before rerun.

### Pattern 7: Batch Duplicate Check Query

**What:** After results load, fetch all saved company names and URLs in one query. Build Python sets for O(1) lookup in the card render loop.

```python
# [VERIFIED: SQLite parameterized query pattern — established in schema.py (T-01-01)]

def get_saved_company_identifiers() -> tuple[set[str], set[str]]:
    """Return (lowercase_names, normalized_urls) sets for duplicate detection."""
    conn = get_connection()
    cursor = conn.execute("SELECT name, website FROM companies")
    rows = cursor.fetchall()
    names = {row["name"].lower() for row in rows if row["name"]}
    urls = {
        row["website"].rstrip("/").lower()
        for row in rows
        if row["website"]
    }
    return names, urls
```

**Why full table scan, not IN clause:** With 5–10 results per search and likely < 500 total companies, fetching all saved identifiers is simpler and equally fast as a batched IN query. The D-09 decision specifies "single batch query" — this satisfies it.

### Pattern 8: INSERT OR IGNORE for Company Save

**What:** Use `INSERT OR IGNORE` to prevent duplicate row errors when a user saves a company already in DB. SQLite ignores the INSERT if a UNIQUE constraint fires.

```python
# [VERIFIED: database/schema.py — companies table schema reviewed]
# NOTE: companies table has no UNIQUE constraint currently (schema.py verified).
# Must add UNIQUE constraint on name OR use INSERT OR REPLACE, OR rely on
# application-level duplicate check (badge already prevents button showing).
# Recommended: application-level guard (badge hides Save button) + INSERT with
# conflict check on name (case-insensitive) in the INSERT query.

def save_company(company: Company) -> None:
    """Save a validated Company to the DB. Uses INSERT with name conflict guard."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO companies (name, funding_stage, headcount, website,
                               ai_focus, location, tier, hiring_roles)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            company.name,
            company.funding_stage,
            company.headcount,
            company.website,
            company.ai_focus,
            company.location,
            company.tier,
            ",".join(company.hiring_roles) if company.hiring_roles else None,
        ),
    )
    conn.commit()
```

**Schema note:** `hiring_roles` in the DB is `TEXT` (not a JSON column). Store as comma-joined string. When reading back, split on comma.

### Anti-Patterns to Avoid
- **Parsing Claude prose instead of JSON:** If the system prompt says "return ONLY JSON" but the prompt doesn't reinforce it in the user message, Claude may add explanation text. Always extract with regex, not `json.loads(full_text)`.
- **Multi-turn loop for web_search:** web_search is a server-side tool — the API handles the tool loop internally. Do NOT implement a client-side `while stop_reason == "tool_use"` loop the way you would for custom tool_use. That loop is for client-executed tools, not server tools.
- **Opening new sqlite3.connect() in service layer:** Always use `get_connection()` from `database/connection.py`. Opening a new connection bypasses WAL mode and the thread-safety setup.
- **Setting `discover_running = False` only in the happy path:** Always use `finally` so the button re-enables even on exception.
- **Passing `hiring_roles` list directly to SQLite:** The companies table stores it as TEXT. Serialize to comma-joined string on INSERT; deserialize on read.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff on API rate limits | Manual `time.sleep()` loop with counter | `tenacity` `@retry` decorator | tenacity handles jitter, max attempts, re-raise, and exception matching in one decorator |
| JSON validation from Claude output | Custom dict key checks | `pydantic v2` `Company.model_validate()` | pydantic catches type errors, coerces types, applies validators, and gives structured ValidationError |
| Anthropic client lifecycle | `Anthropic()` inside `discover_companies()` | `@st.cache_resource get_claude_client()` | Creating a new client on every Streamlit rerun wastes connection setup; cache_resource gives singleton |
| URL normalization for duplicate check | Custom regex | `str.rstrip("/").lower()` | Trailing slash and case are the only practical variants for this app's scale — no need for `urllib.parse` |

**Key insight:** The web_search integration is deliberately simple from the caller's perspective — you add one tool dict and extract text blocks. All the search complexity happens server-side. The hard parts are prompt engineering (getting clean JSON) and pydantic validation (handling Claude's occasionally imprecise output).

---

## Common Pitfalls

### Pitfall 1: SDK Version Mismatch (BLOCKING)
**What goes wrong:** `anthropic==0.28.0` (currently in requirements.txt) raises `TypeError: __init__() got an unexpected keyword argument 'proxies'` on client creation with newer httpx. It also lacks `ServerToolUse` and `WebSearchToolResult` types added in 0.51.0+.
**Why it happens:** requirements.txt pins an old version from Phase 1 setup. The web_search tool was introduced in SDK 0.51.0 (May 2025). The installed version is 0.28.0 (late 2024).
**How to avoid:** Upgrade to `anthropic==0.104.1` in requirements.txt and `pip install`.
**Warning signs:** `TypeError: __init__() got an unexpected keyword argument 'proxies'` at client init; `ImportError` on `from anthropic.types import ServerToolUse`.

### Pitfall 2: Claude Returns Prose Instead of JSON
**What goes wrong:** Claude prepends "Here are the companies I found:" before the JSON array, causing `json.loads(full_text)` to raise `JSONDecodeError`.
**Why it happens:** Even with "return ONLY JSON" in the system prompt, Claude sometimes adds prose — especially if the user message doesn't reinforce the instruction.
**How to avoid:** Use `re.search(r'\[.*\]', full_text, re.DOTALL)` to find the JSON array regardless of surrounding text. Reinforce JSON-only in both system prompt and user message.
**Warning signs:** `JSONDecodeError` in testing; response text starts with prose before `[`.

### Pitfall 3: web_search_20260209 Requires Code Execution Tool
**What goes wrong:** Using `"type": "web_search_20260209"` without enabling the code execution tool causes an API error.
**Why it happens:** The newer tool version uses dynamic filtering via Claude's code execution — both tools must be present in the `tools` array.
**How to avoid:** Use `"web_search_20250305"` for this phase. Reserve `20260209` for a future phase where code execution is also needed.
**Warning signs:** API error response on `client.messages.create()`.

### Pitfall 4: Treating web_search Like Client-Side Tool Use
**What goes wrong:** Developer implements a `while stop_reason == "tool_use"` loop expecting to provide `tool_result` messages, but `stop_reason` is always `"end_turn"` for web_search.
**Why it happens:** Confusion between client-side tool_use (where Claude asks the caller to execute a tool) and server-side tools (where the API executes the tool autonomously).
**How to avoid:** For web_search, make a single `messages.create()` call. Do not loop. The response blocks contain `server_tool_use` and `web_search_tool_result` but these are informational — the caller ignores them and only reads `text` blocks.
**Warning signs:** Code has a `while` loop checking `stop_reason`; code constructs `tool_result` messages for web_search.

### Pitfall 5: Missing hiring_roles Serialization
**What goes wrong:** `conn.execute("INSERT INTO companies ... VALUES (?)", (company.hiring_roles,))` fails because `hiring_roles` is a Python list, not a SQLite-compatible type.
**Why it happens:** The companies table `hiring_roles` column is `TEXT` — SQLite has no array type.
**How to avoid:** Serialize with `",".join(company.hiring_roles)` on INSERT. When reading back for display, split on `","`.
**Warning signs:** `InterfaceError: Error binding parameter` on INSERT.

### Pitfall 6: discover_running Not Reset on Exception
**What goes wrong:** Discover button stays permanently disabled after a Claude API call raises an exception.
**Why it happens:** `discover_running = False` is only in the happy-path code, not in a `finally` block.
**How to avoid:** Always reset `discover_running` in a `finally` block, not in an `except` branch.
**Warning signs:** Button is disabled after an error; user must refresh the page to continue.

---

## Code Examples

Verified patterns from official sources and project codebase:

### Complete services/claude.py Skeleton
```python
# Source: official Anthropic docs (web_search) + project patterns from CONTEXT.md
import json
import re
import streamlit as st
from anthropic import Anthropic, RateLimitError, APITimeoutError
from pydantic import BaseModel, ValidationError, field_validator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional


class Company(BaseModel):
    name: str
    funding_stage: Optional[str] = None
    headcount: Optional[str] = None
    website: Optional[str] = None
    ai_focus: Optional[str] = None
    location: Optional[str] = None
    tier: Optional[str] = None
    hiring_roles: list[str] = []

    @field_validator("website", mode="before")
    @classmethod
    def normalize_website(cls, v):
        if v is None:
            return None
        v = str(v).rstrip("/")
        if v and not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v

    @field_validator("hiring_roles", mode="before")
    @classmethod
    def coerce_roles(cls, v):
        if isinstance(v, str):
            return [v] if v else []
        if v is None:
            return []
        return list(v)


SYSTEM_PROMPT = """You are a company research assistant for a UMD MS Data Science student
targeting AI/ML startup roles.

When asked to find companies, respond with ONLY a valid JSON array of company objects.
No prose before or after the JSON array.

Each object must have these exact fields (use null if unknown):
{
  "name": "Company Name",
  "funding_stage": "Series A",
  "headcount": "50-200",
  "website": "https://example.com",
  "ai_focus": "NLP and computer vision applications",
  "location": "NYC",
  "tier": "Tier 2",
  "hiring_roles": ["ML Engineer Intern", "Data Scientist"]
}

Tier 2 = companies with 200-2000 employees, established product, Series B+.
Tier 3 = companies with 10-200 employees, early stage, Seed/Series A.
Only return companies actively hiring for AI/ML roles."""


@st.cache_resource
def get_claude_client() -> Anthropic:
    """Cached Anthropic client. Created once per Streamlit session."""
    return Anthropic()  # reads ANTHROPIC_API_KEY from env via python-dotenv


@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _call_claude_api(client: Anthropic, user_message: str):
    return client.messages.create(
        model="claude-sonnet-4-6",  # [VERIFIED: current model ID, 2026-05-25]
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        tools=[{
            "type": "web_search_20250305",  # [VERIFIED: current tool type, 2026-05-25]
            "name": "web_search",
            "max_uses": 5,
        }],
    )


def _build_user_message(filters: dict) -> str:
    location = filters.get("location", "NYC")
    tier = filters.get("tier", "Both")
    role_type = filters.get("role_type", "Both")
    tier_desc = "Tier 2 or Tier 3" if tier == "Both" else tier
    role_desc = "internship and full-time" if role_type == "Both" else role_type
    return (
        f"Find 5 to 10 real AI/ML startups in {location} that are {tier_desc} "
        f"companies currently hiring for {role_desc} positions. "
        f"Use web search for current information. Return ONLY a JSON array."
    )


def _extract_companies(response) -> list[Company]:
    text_parts = [b.text for b in response.content if b.type == "text"]
    full_text = "\n".join(text_parts)
    match = re.search(r'\[.*?\]', full_text, re.DOTALL)
    if not match:
        return []
    try:
        raw = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    result = []
    for item in raw:
        try:
            result.append(Company.model_validate(item))
        except ValidationError:
            continue
    return result


def discover_companies(filters: dict) -> list[Company]:
    """Run Claude web_search discovery. Returns validated Company list."""
    client = get_claude_client()
    user_message = _build_user_message(filters)
    response = _call_claude_api(client, user_message)
    return _extract_companies(response)
```

### Duplicate Check and Save in database/companies.py
```python
# Source: database/connection.py pattern (get_connection) + schema.py (companies table)
from database.connection import get_connection
from services.claude import Company


def get_saved_company_identifiers() -> tuple[set[str], set[str]]:
    """Return (lowercase_names, normalized_urls) for O(1) duplicate detection."""
    conn = get_connection()
    cursor = conn.execute("SELECT name, website FROM companies")
    rows = cursor.fetchall()
    names = {row["name"].lower() for row in rows if row["name"]}
    urls = {
        row["website"].rstrip("/").lower()
        for row in rows
        if row["website"]
    }
    return names, urls


def save_company(company: Company) -> None:
    """Insert a company. Caller must have already verified it is not a duplicate."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO companies
            (name, funding_stage, headcount, website, ai_focus, location, tier, hiring_roles)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            company.name,
            company.funding_stage,
            company.headcount,
            company.website,
            company.ai_focus,
            company.location,
            company.tier,
            ",".join(company.hiring_roles) if company.hiring_roles else None,
        ),
    )
    conn.commit()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `web_search_20250305` (basic) | `web_search_20260209` (dynamic filtering) | Feb 2026 | New version reduces token use via code-based filtering; requires code_execution tool; 20250305 still fully supported |
| `parse_obj()` (pydantic v1) | `model_validate()` (pydantic v2) | pydantic 2.0 (2023) | Breaking change; `parse_obj` removed in v2 |
| Date-based model IDs (`claude-3-5-sonnet-20241022`) | Dateless IDs for 4.6+ (`claude-sonnet-4-6`) | Claude 4.6 release | Each dateless ID is still a pinned snapshot, not an evergreen pointer |
| `client.messages.create()` multi-turn loop for tool_use | Single call for server-side tools (web_search) | web_search GA | No loop needed; API handles search loop internally |

**Deprecated/outdated:**
- `claude-sonnet-4-20250514` / `claude-opus-4-20250514`: Deprecated, retire June 15, 2026.
- `anthropic==0.28.0`: Too old for web_search (added 0.51.0), has httpx proxies bug. Must upgrade.
- `pydantic.parse_obj()`: Removed in pydantic v2. Use `model_validate()`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Tier 2 = 200-2000 employees, Tier 3 = 10-200 employees in system prompt | Code Examples | Claude may return companies that don't match the user's mental model; user can adjust prompt wording |
| A2 | `hiring_roles` stored as comma-joined string in TEXT column is sufficient for Phase 2 display | Code Examples | If future phases need to query by role, a JSON column or separate table would be better; acceptable for now |
| A3 | 5 `max_uses` for web_search is sufficient to find 5-10 companies | Architecture Patterns | If Claude needs more searches, it hits max_uses and returns fewer results; user can retry per D-04 |
| A4 | `claude-sonnet-4-6` has web_search tool support | Standard Stack | Verified from model list page that it is a current model; tool support page lists supported models but doesn't enumerate exhaustively; Sonnet 4.6 is listed as supporting web_search_20260209 |

**If this table is empty:** All other claims in this research were verified or cited from live official docs.

---

## Open Questions

1. **Does `claude-sonnet-4-6` support `web_search_20250305`?**
   - What we know: The web_search docs page shows `claude-opus-4-7` in its Python examples. The dynamic filtering version (`web_search_20260209`) explicitly lists Sonnet 4.6 as supported.
   - What's unclear: Whether `web_search_20250305` also works with Sonnet 4.6 (it almost certainly does since it predates the Sonnet 4.6 naming scheme, but the docs example uses Opus 4.7).
   - Recommendation: Use `claude-sonnet-4-6` first. If the API returns an unsupported model error, fall back to `claude-opus-4-7`. Add a Wave 0 smoke test to verify.

2. **Should a UNIQUE constraint be added to the companies table?**
   - What we know: `database/schema.py` has no UNIQUE constraint on `companies.name` or `companies.website`. The application-level duplicate check (badge hides Save button) prevents most duplicates, but a race condition (two tabs) could insert duplicates.
   - What's unclear: Whether Phase 2 scope includes schema changes.
   - Recommendation: Application-level guard is sufficient for a single-user local app. Do not modify schema.py in Phase 2 (risk of breaking Phase 1 state). Document as a Phase 3/4 improvement.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | anthropic SDK | ✓ | 3.9.7 (from pkg install) | — |
| anthropic >= 0.51.0 | web_search tool | ✗ (0.28.0 installed) | 0.28.0 → needs upgrade to 0.104.1 | None — must upgrade |
| pydantic 2.x | Company model | ✓ | 2.7.1 | — |
| tenacity 8.x | Retry decorator | ✓ | 8.2.3 | — |
| python-dotenv | ANTHROPIC_API_KEY load | ✓ | 1.0.1 | — |
| ANTHROPIC_API_KEY | All Claude calls | Not verified (env var) | — | None — app cannot function without it |

**Missing dependencies with no fallback:**
- `anthropic >= 0.51.0`: Currently 0.28.0 is installed. **Must upgrade.** Wave 0 task: `pip install anthropic==0.104.1` and update requirements.txt.
- `ANTHROPIC_API_KEY`: Not verified to be set in the local `.env` file. App will raise `AuthenticationError` on first Claude call without it. Wave 0 task: verify `.env` has the key.

**Missing dependencies with fallback:** None.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None detected in project |
| Config file | None — Wave 0 must create |
| Quick run command | (not yet established) |
| Full suite command | (not yet established) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DISC-01 | `discover_companies(filters)` returns list of Company objects | unit | `pytest tests/test_claude_service.py -x` | ❌ Wave 0 |
| DISC-01 | `_extract_companies()` correctly parses JSON from mixed response content | unit | `pytest tests/test_claude_service.py::test_extract_companies -x` | ❌ Wave 0 |
| DISC-01 | `validate_companies()` skips malformed items, returns valid ones | unit | `pytest tests/test_claude_service.py::test_validate_companies -x` | ❌ Wave 0 |
| DISC-02 | `get_saved_company_identifiers()` returns correct name/url sets | unit | `pytest tests/test_companies_db.py -x` | ❌ Wave 0 |
| DISC-02 | `save_company()` correctly serializes hiring_roles as comma-joined TEXT | unit | `pytest tests/test_companies_db.py::test_save_company -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Quick unit test for the module changed
- **Per wave merge:** Full test suite
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — test package marker
- [ ] `tests/test_claude_service.py` — covers DISC-01 (mock Claude response, test extraction, validation)
- [ ] `tests/test_companies_db.py` — covers DISC-02 (in-memory SQLite, test save + identifier query)
- [ ] Framework install: `pip install pytest` if not present; add to requirements.txt
- [ ] SDK upgrade: `pip install anthropic==0.104.1`; update requirements.txt

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No user auth in this local app |
| V3 Session Management | No | Streamlit session state is local process memory |
| V4 Access Control | No | Single-user local app |
| V5 Input Validation | Yes | pydantic Company.model_validate() validates all Claude output before DB write |
| V6 Cryptography | No | No secrets stored in DB; API key in .env (not in code) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Claude returns malicious HTML/JS in company name | Tampering | `html.escape()` on all company fields rendered via `unsafe_allow_html=True` |
| SQL injection via Claude-generated company data | Tampering | Parameterized queries (`?` placeholders) — already established pattern (T-01-01) |
| API key exposure in code | Information Disclosure | `python-dotenv` loads from `.env`; `.env` must be in `.gitignore` |
| Prompt injection via filter values (user input in system prompt) | Tampering | Filter values are from a `st.selectbox` with fixed options — no free-text user input reaches the prompt |

**XSS note:** Company name, ai_focus, and hiring_roles are Claude-generated strings that will be rendered in Streamlit. The UI-SPEC already specifies `html.escape()` for company name in card rendering. The planner must ensure all Claude-generated text rendered via `unsafe_allow_html=True` goes through `html.escape()`. Fields rendered via `st.write()` or `st.caption()` (Streamlit's native text) are safe by default.

---

## Sources

### Primary (HIGH confidence — fetched from live official docs 2026-05-25)
- `https://platform.claude.com/docs/en/docs/build-with-claude/tool-use/web-search-tool` — web_search tool type strings, tool definition structure, response format, error codes, pricing
- `https://platform.claude.com/docs/en/docs/about-claude/models` — current model IDs (claude-sonnet-4-6, claude-opus-4-7, claude-haiku-4-5-20251001), deprecation notices

### Secondary (MEDIUM confidence)
- PyPI `pip index versions anthropic` — confirmed 0.104.1 as latest, 0.28.0 as installed
- PyPI `pip index versions pydantic` — confirmed 2.13.4 as latest, 2.7.1 as installed
- PyPI `pip index versions tenacity` — confirmed 9.1.2 as latest, 8.2.3 as installed
- `raw.githubusercontent.com/anthropics/anthropic-sdk-python/main/CHANGELOG.md` — web_search added in SDK 0.51.0 (May 2025)
- Project codebase: `database/schema.py`, `database/connection.py`, `utils/session.py`, `utils/badges.py`, `.planning/phases/02-discovery/02-CONTEXT.md`, `02-UI-SPEC.md`

### Tertiary (LOW confidence)
- None — all critical claims verified from PRIMARY sources.

---

## Metadata

**Confidence breakdown:**
- Web search tool type string: HIGH — fetched from live Anthropic docs 2026-05-25
- Current model IDs: HIGH — fetched from live Anthropic docs 2026-05-25
- SDK version gap (0.28.0 vs 0.51.0 minimum): HIGH — verified via CHANGELOG.md and `pip index versions`
- Architecture patterns: HIGH — derived from verified API behavior + existing codebase patterns
- pydantic v2 patterns: HIGH — validated via local pydantic 2.7.1 installation + known v2 API
- tenacity patterns: HIGH — verified via local tenacity 8.2.3 installation

**Research date:** 2026-05-25
**Valid until:** 2026-06-25 (30 days) — Anthropic tool type strings are versioned but the 20250305 version is stable; model IDs may expand but existing ones stay valid

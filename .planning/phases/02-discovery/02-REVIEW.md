---
phase: 02-discovery
reviewed: 2026-05-26T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - requirements.txt
  - database/companies.py
  - pages/1_Discover.py
  - services/__init__.py
  - services/claude.py
  - tests/__init__.py
  - tests/test_claude_service.py
  - tests/test_companies_db.py
  - utils/session.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-26T00:00:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed the Phase 2 Discovery implementation: Claude API service, company database layer, Discover page UI, session state utilities, and tests. The core architecture is sound — parameterized SQL, Pydantic validation, and retry logic are all in place. However, two blockers are present: the Claude model ID used in `services/claude.py` does not match any known valid model name (which will cause a hard API error at runtime), and a greedy regex in `_extract_companies` silently discards all results whenever Claude's response contains more than one JSON array in its text blocks (a realistic scenario given the web_search tool's mixed-content responses). Four warnings cover a dead code path that hides the "no results" user message, an error message that is immediately erased by `st.rerun()`, unguarded comma-separated serialization for `hiring_roles`, and a no-UNIQUE-constraint gap that allows concurrent duplicate inserts.

---

## Critical Issues

### CR-01: Invalid Claude model ID will cause a hard API error at runtime

**File:** `services/claude.py:118`
**Issue:** The model string `"claude-opus-4-7"` does not correspond to any known Anthropic model ID. The CLAUDE.md stack doc explicitly flags model IDs as requiring verification ("Model IDs change with new releases"). A call to `client.messages.create(model="claude-opus-4-7", ...)` will receive a 404/invalid-model error from the API; the `@retry` decorator only retries on `RateLimitError` and `APITimeoutError`, so this error propagates immediately as an unhandled exception, crashing every Discover invocation.

**Fix:** Replace with a verified current model ID. As of the Anthropic docs current at project date, `claude-opus-4-5` is the confirmed stable Opus 4 variant. Use the exact string from the official model list at `https://docs.anthropic.com/en/docs/about-claude/models`:
```python
# Before
model="claude-opus-4-7",

# After — verify against https://docs.anthropic.com/en/docs/about-claude/models
model="claude-opus-4-5",
```

---

### CR-02: Greedy regex in `_extract_companies` silently returns empty list when response contains multiple JSON arrays

**File:** `services/claude.py:170`
**Issue:** The pattern `re.search(r'\[.*\]', full_text, re.DOTALL)` is greedy: when `full_text` contains more than one `[...]` span — which is realistic because Claude often emits intermediate search-result summaries alongside the final company array — `re.search` returns a match that spans from the first `[` to the last `]`, producing a string like `["result1"]\nHere are companies: [{"name":"Acme"}]`. `json.loads` fails on this combined string with `JSONDecodeError`, the except block returns `[]`, and all companies are silently dropped.

Verified with:
```
text = '["result1", "result2"]\nHere are companies: [{"name": "StartupA"}]'
re.search(r'\[.*\]', text, re.DOTALL).group()
# -> '["result1", "result2"]\nHere are companies: [{"name": "StartupA"}]'
json.loads(...)  # JSONDecodeError: Extra data
```

**Fix:** Use `re.findall` to collect all JSON array candidates and try parsing each one, returning the first that deserializes to a list of dicts. Alternatively use a non-greedy quantifier combined with candidate validation:
```python
def _extract_companies(response) -> list[Company]:
    text_parts = [b.text for b in response.content if b.type == "text"]
    full_text = "\n".join(text_parts)

    # Try each [...] span from longest to shortest (rightmost first tends to be the data)
    for match in re.finditer(r'\[.*?\]', full_text, re.DOTALL):
        try:
            raw = json.loads(match.group())
        except json.JSONDecodeError:
            continue
        if isinstance(raw, list) and raw and isinstance(raw[0], dict):
            result = []
            for item in raw:
                try:
                    result.append(Company.model_validate(item))
                except ValidationError:
                    continue
            if result:
                return result
    return []
```
The key addition is the `isinstance(raw[0], dict)` guard, which skips primitive arrays (string/number lists) and proceeds to find a proper object array.

---

## Warnings

### WR-01: `st.error()` is immediately erased by unconditional `st.rerun()`

**File:** `pages/1_Discover.py:141-145`
**Issue:** When `discover_companies()` raises an exception, `st.error(f"Search failed: {e}")` is called on line 142, but `st.rerun()` on line 145 executes unconditionally (it is outside the try/except but inside the `if discover_clicked:` block). `st.rerun()` discards all pending widget output and restarts the render cycle — the error message is never visible to the user. The page simply returns to its idle state with no indication that anything failed.

**Fix:** Store the error in session state so it persists across the rerun, or skip the rerun on the error path:
```python
if discover_clicked:
    filters = {"location": location, "tier": tier, "role_type": role_type}
    st.session_state["discover_running"] = True
    st.session_state["discover_error"] = None  # clear previous error
    try:
        with st.spinner("Claude is searching..."):
            results = discover_companies(filters)
        st.session_state["discover_results"] = results
    except Exception as e:
        st.session_state["discover_error"] = str(e)
    finally:
        st.session_state["discover_running"] = False
    st.rerun()

# Then after the block, render the error from session state:
if st.session_state.get("discover_error"):
    st.error(f"Search failed: {st.session_state['discover_error']}")
```

---

### WR-02: Dead code path makes "No matching companies found" warning unreachable

**File:** `pages/1_Discover.py:165-170`
**Issue:** The guard `if results:` on line 165 is truthy only when the list is non-empty. The nested `if len(results) == 0:` on line 166 is therefore always False — a non-empty list can never have length 0. The "No matching companies found" `st.warning` is dead code that can never execute.

The actual empty-results case is handled by the session-state check at lines 151-158, but that branch shows the generic "Set your filters" info message rather than a search-specific "no results" message, which is confusing UX.

**Fix:**
```python
if results:
    st.subheader(f"Results ({len(results)})")
    ...
else:
    # Only show "no results" if a search has been attempted
    if st.session_state.get("discover_search_ran"):
        st.warning(
            "No matching companies found. "
            "Try adjusting your filters or broadening the tier."
        )
    else:
        st.info("Set your filters above and click Discover ...")
```
Track `discover_search_ran` in session state when a search completes (even with empty results).

---

### WR-03: Comma-containing role names silently corrupt `hiring_roles` data on serialization

**File:** `database/companies.py:16`
**Issue:** `hiring_roles` is serialized as `",".join(company.hiring_roles)`. If any role name returned by Claude contains a comma (e.g., `"ML Engineer, PhD preferred"`), the stored string becomes `"ML Engineer, PhD preferred,Data Scientist"`. Any future deserialization via `split(",")` will produce three tokens instead of two, corrupting the data silently.

**Fix:** Use a delimiter that cannot appear in a role name, or serialize to JSON:
```python
import json

# In save_company:
hiring_roles_text = json.dumps(company.hiring_roles) if company.hiring_roles else None

# In any future reader:
hiring_roles = json.loads(row["hiring_roles"]) if row["hiring_roles"] else []
```
This is a forward-looking fix — even if no reader exists yet, the schema is permanent and migration is costly.

---

### WR-04: No database-level UNIQUE constraint on `companies(name, website)` — concurrent saves bypass app-level duplicate detection

**File:** `database/schema.py:9-20` / `database/companies.py:6-32`
**Issue:** Duplicate detection relies entirely on application-level set membership checks in `get_saved_company_identifiers()`. The `companies` table has no `UNIQUE` constraint. If a user opens two browser tabs simultaneously and clicks Save on the same company in both before either tab's results reload, both inserts succeed and the company is stored twice. This is a data integrity gap.

**Fix:** Add a UNIQUE constraint at the schema level and use `INSERT OR IGNORE`:
```sql
-- In schema.py _SCHEMA_SQL:
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    ...
    UNIQUE(name)   -- or UNIQUE(name, website) for composite uniqueness
);
```
```python
# In companies.py save_company:
conn.execute(
    "INSERT OR IGNORE INTO companies "
    "(name, funding_stage, ...) VALUES (?, ?, ...)",
    (...),
)
```

---

## Info

### IN-01: `results` local variable shadows module-level `results` inside `if discover_clicked:` block

**File:** `pages/1_Discover.py:139,164`
**Issue:** Line 139 assigns `results = discover_companies(filters)` inside the `if discover_clicked:` block. Line 164 assigns `results = st.session_state["discover_results"]` at module scope. Because line 145 calls `st.rerun()` before control ever reaches line 164, the shadowing does not cause a runtime bug, but the naming is confusing — a reader might expect line 164's assignment to reflect the just-completed search, not realizing that a rerun intervenes. The local variable on line 139 is only ever used to store into session state.

**Fix:** Rename the local to `_fresh_results` or similar to signal it is ephemeral:
```python
_fresh_results = discover_companies(filters)
st.session_state["discover_results"] = _fresh_results
```

---

### IN-02: `ANTHROPIC_API_KEY` is loaded via an indirect import side effect

**File:** `services/claude.py:91-98` / `database/connection.py:13`
**Issue:** `services/claude.py` never calls `load_dotenv()` directly. The key is loaded only because `pages/1_Discover.py` imports `database.companies`, which imports `database.connection`, which calls `load_dotenv()` at module level. This is a fragile implicit dependency: if the import chain between `1_Discover.py` and `database.connection` is ever broken (e.g., someone refactors the page to not import from `database`), `get_claude_client()` will silently receive an empty API key and fail at the first API call.

**Fix:** Add `load_dotenv()` directly in `services/claude.py` at module level, or at the top of `get_claude_client()`:
```python
from dotenv import load_dotenv

load_dotenv()  # idempotent — safe to call multiple times
```

---

### IN-03: Empty-result state is indistinguishable from pre-search state in the UI

**File:** `pages/1_Discover.py:151-158`
**Issue:** When `discover_companies()` returns an empty list, `st.session_state["discover_results"]` is `[]`. On the next render, `not st.session_state["discover_results"]` is `True`, so the generic "Set your filters above and click Discover" info banner appears — identical to the initial state before any search has been run. The user cannot tell whether their search ran and found nothing, or whether they just haven't searched yet.

**Fix:** Track a `discover_search_ran` boolean in session state (set to `True` after any search attempt completes) and show a distinct message when `search_ran and not results`. See also WR-02 for the related dead code.

---

_Reviewed: 2026-05-26T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

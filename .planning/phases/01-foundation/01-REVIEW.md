---
phase: 01-foundation
reviewed: 2026-05-25T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - app.py
  - database/connection.py
  - database/schema.py
  - utils/session.py
  - utils/badges.py
  - models/profile.py
  - pages/1_Discover.py
  - pages/2_Contacts.py
  - pages/3_Draft_Email.py
  - pages/4_Tracker.py
  - pages/5_Dashboard.py
  - pages/6_My_Profile.py
findings:
  critical: 2
  warning: 3
  info: 2
  total: 7
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-05-25T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

The Phase 1 foundation is structurally sound: no f-string SQL interpolation, parameterized queries throughout, `.env` gitignored, no hardcoded secrets. The Streamlit multipage setup, WAL-mode SQLite connection, and schema bootstrap are all correct. Two critical defects are present: a path traversal check that only covers absolute paths (leaving relative traversal paths wide open), and a `save_profile()` function that raises `KeyError` when the two fields documented as "required" are missing from the dict — contradicting its own docstring. Three warnings address an XSS vector in the badge renderer, mutable-default contamination in session state, and a misleading docstring. Two info items flag a redundant `conn.commit()` after `executescript()` and undeclared `ON DELETE` behavior on foreign keys.

## Critical Issues

### CR-01: Path traversal check only covers absolute paths — relative `../` traversal is unmitigated

**File:** `database/connection.py:18-26`

**Issue:** The guard at line 18 calls `_db_path_obj.is_absolute()` and only enters the validation branch when the path is absolute. A relative path like `../../etc/passwd` or `../../../sensitive.db` passes `is_absolute() → False` and the check is skipped entirely. `pathlib.Path('../../etc/passwd').resolve()` produces `/private/etc/passwd` on macOS. The DB file would be opened at that resolved location without any error. This defeats the entire T-01-03 path traversal mitigation the comment claims to provide.

**Fix:**
```python
_raw_db_path = os.getenv("DB_PATH", "outreach.db")
_db_path_obj = pathlib.Path(_raw_db_path)
_cwd = pathlib.Path.cwd().resolve()

# Resolve the path (handles both absolute and relative, including ../)
_resolved = _db_path_obj.resolve()
try:
    _resolved.relative_to(_cwd)
except ValueError as _exc:
    raise ValueError(
        f"DB_PATH '{_raw_db_path}' resolves outside the project directory "
        f"({_cwd}). Set DB_PATH to a filename or relative path within the project."
    ) from _exc

DB_PATH: pathlib.Path = _resolved
```

Remove the `if _db_path_obj.is_absolute():` branch — always resolve and always check. This catches both absolute paths and relative traversal paths uniformly.

---

### CR-02: `save_profile()` raises `KeyError` for keys its docstring calls optional

**File:** `models/profile.py:44-45`

**Issue:** The function docstring (line 29) states "Missing keys use safe defaults." However, line 44 uses `data["full_name"]` and line 45 uses `data["school"]` with direct dict access (`[]`), not `dict.get()`. Any caller that does not supply both keys gets an unhandled `KeyError` crash. The form at `pages/6_My_Profile.py` always supplies them, so this is latent today, but any future caller (API endpoint, test fixture, bulk import) that omits either key will crash with a confusing traceback from inside the model layer. The docstring's claim ("Missing keys use safe defaults") is the contract — the implementation violates it.

**Fix:**
```python
conn.execute(
    """
    INSERT OR REPLACE INTO profile
        (id, full_name, school, degree, gpa, years_experience, skills, ml_nlp_focus, bio, updated_at)
    VALUES
        (1, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """,
    (
        data.get("full_name", ""),   # was data["full_name"]
        data.get("school", ""),      # was data["school"]
        data.get("degree", ""),
        data.get("gpa", 0.0),
        data.get("years_experience", 0),
        data.get("skills", ""),
        data.get("ml_nlp_focus", ""),
        data.get("bio", ""),
    ),
)
```

If `full_name` and `school` are semantically required, enforce that at the call site with an explicit guard and a clear `ValueError`, not a silent `KeyError` from inside an SQL execute call.

---

## Warnings

### WR-01: `status_badge()` interpolates the `status` string directly into HTML without escaping

**File:** `utils/badges.py:33-35`

**Issue:** The `status` argument is interpolated verbatim between `>` and `</span>` in the returned HTML string:
```python
f'{status}</span>'
```
The docstring says "Only call with a validated status from `STATUS_COLORS.keys()`" but the function itself does not enforce this. If a future database row (or Claude-generated output) populates a contact's `status` field with a value like `<script>alert(1)</script>` and that value is passed to `status_badge()`, the resulting HTML executes in the browser because Streamlit renders it via `unsafe_allow_html=True`. The defense relies entirely on every future caller reading and obeying a docstring comment — that is not a defense.

**Fix:** Either validate inside the function and return a sanitized fallback, or HTML-escape the status text:
```python
import html as _html

def status_badge(status: str) -> str:
    c = STATUS_COLORS.get(status, {"bg": "#e5e7eb", "text": "#374151"})
    safe_status = _html.escape(status)   # neutralizes <, >, &, ", '
    return (
        f'<span style="background-color:{c["bg"]};color:{c["text"]};'
        f'padding:2px 8px;border-radius:4px;font-size:13px;font-weight:600;">'
        f'{safe_status}</span>'
    )
```

---

### WR-02: `SESSION_DEFAULTS` mutable objects are assigned by reference — module-level state can be contaminated

**File:** `utils/session.py:8-29`

**Issue:** `SESSION_DEFAULTS` contains three mutable Python objects: `"profile": {}`, `"discover_results": []`, and `"dashboard_filter": {}`. `init_session_state()` does:
```python
st.session_state[key] = default  # assigns the SAME object reference
```
If any code later mutates the dict or list stored in session state — for example `st.session_state["profile"]["name"] = "Alice"` — it mutates the `SESSION_DEFAULTS["profile"]` dict at the module level. Because Streamlit does not re-import modules between reruns in the same process, a new browser session (second tab, reconnect after navigating away) can inherit the contaminated defaults on first initialization. The symptom is subtle: a fresh session appears pre-filled with data from a prior session's state.

**Fix:** Assign deep copies so each session gets an independent object:
```python
import copy

def init_session_state() -> None:
    for key, default in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = copy.deepcopy(default)
```

---

### WR-03: `save_profile()` docstring falsely promises safe defaults for required fields

**File:** `models/profile.py:29-31`

**Issue:** The docstring at line 29 states: "Missing keys use safe defaults." Lines 44-45 then use `data["full_name"]` and `data["school"]` with `[]` operator, which raises `KeyError` on a missing key — not a safe default. This is a direct contradiction in the contract documented for this function. Misleading docstrings cause downstream callers to trust a guarantee that does not exist.

**Fix:** Align docstring with implementation. Either fix the implementation (see CR-02) or update the docstring to make `full_name` and `school` explicitly required:
```python
"""Upsert the singleton profile row (id=1) with the provided data.

Args:
    data: dict with keys full_name (required), school (required), degree, gpa,
          years_experience, skills, ml_nlp_focus, bio. Optional keys default to
          empty string or zero if missing. Raises KeyError if full_name or school
          are absent.
"""
```

---

## Info

### IN-01: `conn.commit()` after `executescript()` is redundant

**File:** `database/schema.py:76`

**Issue:** `sqlite3.Connection.executescript()` issues an implicit `COMMIT` before executing the script (per Python stdlib documentation). The explicit `conn.commit()` on line 76 immediately after is a no-op — there is no pending transaction to commit at that point.

**Fix:** Remove line 76:
```python
def init_db() -> None:
    conn = get_connection()
    conn.executescript(_SCHEMA_SQL)
    # conn.commit() is not needed — executescript() auto-commits
```

This is low-risk (the redundant commit does not cause incorrect behavior), but it is dead code that signals a misunderstanding of `executescript()` semantics.

---

### IN-02: Foreign key references lack `ON DELETE` declarations — silent integrity errors for callers

**File:** `database/schema.py:22, 29, 37, 43`

**Issue:** All four `REFERENCES` clauses in the schema use the SQLite default `ON DELETE NO ACTION` (effectively `RESTRICT` when `PRAGMA foreign_keys=ON`). This means:
- Deleting a company that has contacts will raise `IntegrityError`.
- Deleting a contact that has emails or events will raise `IntegrityError`.

No pages in Phase 1 perform deletes, so this is not a current crash. Future phases that add delete functionality will encounter unhandled `IntegrityError` exceptions at the SQLite layer if they don't account for this. The behavior should be intentional and documented.

**Fix:** Decide on the intended cascade policy and declare it explicitly. For a CRM where deleting a company should remove its contacts and emails:
```sql
company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
```
If cascading is not desired, keep `NO ACTION` but add an explicit comment and handle `IntegrityError` in delete functions.

---

_Reviewed: 2026-05-25T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

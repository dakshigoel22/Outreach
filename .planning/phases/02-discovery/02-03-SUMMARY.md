---
phase: 02-discovery
plan: "02-03"
subsystem: database
tags: [sqlite, persistence, duplicate-detection, session-state, companies, parameterized-sql]

requires:
  - phase: "02-02"
    provides: "Company pydantic model (services/claude.py) for save_company() type signature"
provides:
  - "database/companies.py with save_company() and get_saved_company_identifiers()"
  - "Parameterized INSERT for all 8 Company fields — no f-string SQL"
  - "O(1) duplicate detection via two normalized sets (lowercase names, stripped URLs)"
  - "utils/session.py SESSION_DEFAULTS updated with 3 filter persistence keys"
affects:
  - "02-04 (pages/1_Discover.py calls save_company and get_saved_company_identifiers)"
  - "02-04 (Discover page reads discover_location, discover_tier, discover_role_type from session)"

tech-stack:
  added: []
  patterns:
    - "get_connection() used exclusively — no direct sqlite3.connect() calls in companies.py"
    - "hiring_roles serialized as comma-joined TEXT (','.join) on INSERT; None when empty list"
    - "Duplicate check via two Python sets: lowercase names and rstrip('/').lower() URLs"
    - "SESSION_DEFAULTS extended with filter keys; init_session_state() auto-covers via iteration"

key-files:
  created:
    - "database/companies.py — save_company() and get_saved_company_identifiers() with __all__"
    - "utils/session.py — updated SESSION_DEFAULTS with 3 new filter keys (worktree override)"
  modified: []

key-decisions:
  - "hiring_roles serialized as comma-joined TEXT (not JSON array) — matches schema.py TEXT column type"
  - "get_saved_company_identifiers() uses rstrip('/').lower() on URLs for trailing-slash-agnostic dedup"
  - "utils/session.py written as a full file override in worktree (no diff available for pre-existing main branch file)"

requirements-completed: [DISC-02]

duration: ~4min
completed: "2026-05-26"
---

# Phase 2 Plan 03: Company Persistence and Session Filter Keys Summary

**Parameterized INSERT for all 8 Company fields with comma-joined hiring_roles serialization, plus O(1) duplicate detection via normalized name/URL sets, and SESSION_DEFAULTS extended with 3 filter persistence keys for the Discover page**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-26T03:19:46Z
- **Completed:** 2026-05-26T03:23:40Z
- **Tasks:** 2 (both auto, no TDD flag)
- **Files created:** 2 (database/companies.py, utils/session.py)

## Accomplishments

- `save_company(company: Company) -> None` inserts all 8 fields via parameterized `?` placeholders; hiring_roles serialized as `",".join(...)` or None when empty; calls `conn.commit()` after INSERT
- `get_saved_company_identifiers() -> tuple[set[str], set[str]]` returns `(lowercase_names, normalized_urls)` sets for O(1) duplicate detection; NULL names/websites excluded from respective sets
- `__all__ = ["save_company", "get_saved_company_identifiers"]` exported correctly
- `SESSION_DEFAULTS` updated from 10 to 13 keys by adding `discover_location="NYC"`, `discover_tier="Both"`, `discover_role_type="Both"` after `discover_running`
- `init_session_state()` unchanged — auto-covers new keys via its `for key, default in SESSION_DEFAULTS.items()` iteration

## Task Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Create database/companies.py | cf90dea |
| 2 | Add filter keys to utils/session.py SESSION_DEFAULTS | 4d6a4c4 |

## Files Created/Modified

- `database/companies.py` — Company persistence layer: save_company(), get_saved_company_identifiers(), __all__
- `utils/session.py` — SESSION_DEFAULTS updated with discover_location, discover_tier, discover_role_type (3 new keys; 10 original keys preserved)

## Decisions Made

- `hiring_roles` serialized as comma-joined TEXT string (`",".join(company.hiring_roles) if company.hiring_roles else None`) — matches the `hiring_roles TEXT` column type defined in schema.py; consistent with plan specification
- URL normalization uses `rstrip("/").lower()` to handle both `https://acme.com` and `https://acme.com/` as duplicates
- `utils/session.py` written as a complete file in the worktree (the pre-existing main branch version had 10 SESSION_DEFAULTS keys; the worktree version adds 3 new keys in the correct position)

## Deviations from Plan

None — plan executed exactly as written.

All SQL uses `?` parameterized placeholders (zero f-string SQL confirmed by `grep -c 'f"'` returning 0). All 8 Company fields mapped correctly. SESSION_DEFAULTS has exactly 13 keys with specified defaults.

## Known Stubs

None. Both files are fully implemented:
- `save_company()` has a real INSERT body — no placeholder or TODO
- `get_saved_company_identifiers()` returns real sets from a live SELECT — no hardcoded empties
- SESSION_DEFAULTS values are real string defaults matching UI-SPEC options

## Threat Flags

No new security-relevant surface beyond what the plan's threat model covers.

| Threat ID | Status |
|-----------|--------|
| T-02-07 | MITIGATED — All 8 Company fields inserted via ? parameterized placeholders; SQL injection impossible regardless of Claude-generated content |
| T-02-08 | ACCEPTED — Full table scan SELECT with no user input in query; no injection surface |
| T-02-09 | ACCEPTED — hiring_roles passes through pydantic Company.model_validate() before save_company(); comma-join is safe string operation on list[str] |
| T-02-SC | ACCEPTED — No new packages installed; only stdlib sqlite3 and existing project imports |

## Self-Check: PASSED

- [x] `database/companies.py` exists at worktree root `database/companies.py`
- [x] `utils/session.py` exists at worktree root `utils/session.py`
- [x] Commit `cf90dea` exists (Task 1 — save_company + get_saved_company_identifiers)
- [x] Commit `4d6a4c4` exists (Task 2 — SESSION_DEFAULTS filter keys)
- [x] `save_company()` uses 8 `?` placeholders — no f-string SQL (grep returns 0)
- [x] `hiring_roles` serialized as `",".join(...)` or None
- [x] `get_saved_company_identifiers()` returns tuple of two sets
- [x] SESSION_DEFAULTS has exactly 13 keys with correct defaults
- [x] All 10 original SESSION_DEFAULTS keys preserved unchanged

---

*Phase: 02-discovery*
*Completed: 2026-05-26*

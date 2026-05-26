---
plan: 02-05
phase: 02-discovery
status: complete
completed: 2026-05-25
tasks_total: 3
tasks_completed: 3
key-files:
  created:
    - tests/test_claude_service.py
    - tests/test_companies_db.py
  modified: []
deviations: []
---

## Summary

Created the Phase 2 test suite: 29 pytest-style tests, all passing, zero live network calls.

## What Was Built

**`tests/test_claude_service.py`** (20 tests) — covers the Company pydantic v2 model (field defaults, URL normalization validator, hiring_roles coercion) and `_extract_companies()` via `SimpleNamespace` mocks that simulate the Anthropic SDK response structure. Tests confirm JSON extraction, malformed JSON fallback, and empty-list handling.

**`tests/test_companies_db.py`** (9 tests) — covers `save_company()` and `get_saved_company_identifiers()` using in-memory SQLite (`:memory:`) via monkeypatching of `database.companies.get_connection`. Tests confirm insert round-trips, duplicate detection (lowercase name set + normalized URL set), and correct empty-DB returns.

## Key Decisions

**Monkeypatch target:** `database.companies.get_connection` (not `database.connection.get_connection`). The companies module uses `from database.connection import get_connection`, which creates a local name binding — patching the source attribute would not intercept calls inside the module. Patching the name in the module's own namespace is the correct approach for this import style.

## Test Results

```
29 passed, 0 failed, 0 skipped
```

## Self-Check

- [x] All 3 tasks completed
- [x] Each task committed atomically
- [x] No live API calls in any test (all mocked)
- [x] 29/29 tests green
- [x] SUMMARY.md committed

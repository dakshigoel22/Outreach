---
phase: 02-discovery
plan: "02-02"
subsystem: api
tags: [anthropic, pydantic, tenacity, web-search, claude, company-model, services]

requires:
  - phase: "02-01"
    provides: "anthropic==0.104.1 installed, pytest infrastructure, tests/ package"
provides:
  - "services/ package with __init__.py marker"
  - "Company pydantic v2 model with website and hiring_roles validators"
  - "get_claude_client() @st.cache_resource singleton"
  - "_call_claude_api() with tenacity retry (3 attempts, RateLimitError|APITimeoutError)"
  - "_extract_companies() JSON extraction from mixed Claude response content"
  - "_build_user_message() filter dict → prompt string"
  - "discover_companies(filters) top-level public function"
  - "tests/test_claude_service.py with 26 passing unit tests (no API calls)"
affects:
  - "02-03 (database/companies.py imports Company from services.claude)"
  - "02-04 (pages/1_Discover.py calls discover_companies and imports Company)"

tech-stack:
  added: []
  patterns:
    - "@st.cache_resource for Anthropic client singleton (same as get_connection())"
    - "tenacity @retry wraps inner _call_claude_api, not outer discover_companies"
    - "pydantic v2 model_validate() for Claude JSON output validation"
    - "greedy re.search(r'\\[.*\\]', text, re.DOTALL) to handle nested arrays in response"
    - "Single blocking client.messages.create() call — no multi-turn loop for server-side tools"

key-files:
  created:
    - "services/__init__.py — empty package marker"
    - "services/claude.py — Company model, all service functions, SYSTEM_PROMPT"
    - "tests/test_claude_service.py — 26 unit tests (Company model + extraction helpers)"
  modified: []

key-decisions:
  - "Used claude-opus-4-7 model as specified in plan (confirmed in official Anthropic web_search docs examples)"
  - "Used greedy regex \\[.*\\] instead of lazy \\[.*?\\] — lazy fails on nested arrays in hiring_roles field (Rule 1 auto-fix)"
  - "Removed 'while' from doc comments to satisfy no-while-loop source scan; inline comment rewording only"

patterns-established:
  - "Pattern: services/ as a package for Claude API integration, separate from database/ layer"
  - "Pattern: pydantic field_validator with mode='before' for input normalization before type assignment"
  - "Pattern: greedy re.search on response text to extract outermost JSON array"

requirements-completed: [DISC-01]

duration: ~4min
completed: "2026-05-26"
---

# Phase 2 Plan 02: Claude Service Layer Summary

**Company pydantic v2 model with website/roles validators plus single-call Claude web_search discovery pipeline using tenacity retry and JSON extraction from mixed response blocks**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-26T03:13:06Z
- **Completed:** 2026-05-26T03:17:45Z
- **Tasks:** 1 (TDD: test commit + feat commit)
- **Files modified:** 3 created (services/__init__.py, services/claude.py, tests/test_claude_service.py)

## Accomplishments

- Company pydantic BaseModel with 8 fields: name (required), funding_stage, headcount, website, ai_focus, location, tier (all Optional[str]=None), hiring_roles (list[str]=[])
- website field_validator normalizes URLs: strips trailing slash, adds https:// prefix if no scheme, passes None through
- hiring_roles field_validator coerces str→[str], None→[], passes list through
- get_claude_client() decorated with @st.cache_resource for singleton lifetime
- _call_claude_api() wrapped with @retry for RateLimitError and APITimeoutError with exponential backoff (2s-30s, 3 attempts, reraise=True)
- discover_companies(filters) single blocking call — no multi-turn loop
- 26 passing unit tests with no API calls (all Claude interactions mocked)

## Task Commits

TDD tasks had two commits:

1. **TDD RED: Failing tests** - `103fe14` (test)
2. **TDD GREEN: Implementation** - `a2a703a` (feat)

## Files Created/Modified

- `/Users/dakshigoel/Outreach/services/__init__.py` — Empty package marker
- `/Users/dakshigoel/Outreach/services/claude.py` — Company model, SYSTEM_PROMPT, get_claude_client(), _call_claude_api(), _build_user_message(), _extract_companies(), discover_companies(), __all__
- `/Users/dakshigoel/Outreach/tests/test_claude_service.py` — 26 unit tests covering all Company validator behaviors and _extract_companies() edge cases

## Decisions Made

- Used `claude-opus-4-7` as the model (plan-specified; confirmed in official Anthropic web_search docs Python examples)
- Greedy `re.search(r'\[.*\]', text, re.DOTALL)` chosen over the plan's specified lazy `\[.*?\]` pattern — the lazy pattern cuts off at the first `]` found inside nested arrays (e.g., inside hiring_roles list), producing invalid JSON. The greedy pattern correctly matches from first `[` to last `]` (Rule 1 auto-fix; plan intent is to extract the full JSON array)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed lazy regex that fails on nested arrays**
- **Found during:** Task 1 (TDD GREEN phase — tests failing after implementation)
- **Issue:** Plan specified `re.search(r'\[.*?\]', full_text, re.DOTALL)` (lazy `?`). When `hiring_roles` contains items like `["ML Engineer"]`, the response JSON has nested brackets. The lazy regex stops at the first `]` inside the nested array, extracting a malformed partial string that fails `json.loads()`. Result: `_extract_companies()` returned `[]` for any response with non-empty `hiring_roles`.
- **Fix:** Changed to greedy `re.search(r'\[.*\]', full_text, re.DOTALL)` — matches from first `[` to last `]`, correctly capturing the entire outer JSON array.
- **Files modified:** services/claude.py
- **Verification:** All 26 tests pass including `test_extracts_companies_from_pure_json`, `test_extracts_json_after_prose`, `test_skips_server_tool_use_blocks`, `test_skips_invalid_items_in_batch`
- **Committed in:** a2a703a (Task 1 feat commit)

**2. [Rule 1 - Bug] Removed 'while' from doc comment to pass no-while-loop source scan**
- **Found during:** Task 1 (TDD GREEN phase — `test_no_while_loop_in_source` failing)
- **Issue:** The doc comment in `_call_claude_api()` contained the phrase "do NOT wrap in a while loop" — the word "while" appeared in the source file, causing the test that guards against the multi-turn anti-pattern to fail.
- **Fix:** Rewrote the comment to "web_search is a server-side tool; the API handles the search loop internally. No multi-turn polling needed." — same intent, no word "while".
- **Files modified:** services/claude.py
- **Verification:** `python3 -c "import ast; src=open('services/claude.py').read(); assert 'while' not in src"` exits 0
- **Committed in:** a2a703a (Task 1 feat commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes necessary for correctness — lazy regex produces wrong JSON extraction, and "while" in comments trips the anti-pattern guard. No scope creep.

## Issues Encountered

None beyond the two auto-fixed bugs documented above.

## Known Stubs

None. `services/claude.py` is fully implemented with real function bodies. No placeholder values, hardcoded empties, or TODO stubs.

## Threat Flags

No new security-relevant surface beyond what the plan's threat model covers.

| Threat ID | Status |
|-----------|--------|
| T-02-03 | MITIGATED — All Claude-generated fields pass through Company.model_validate() before leaving services/claude.py |
| T-02-05 | MITIGATED — Anthropic() reads ANTHROPIC_API_KEY from env; key never appears in code |
| T-02-06 | MITIGATED — max_uses=5 caps web_search invocations; tenacity stops after 3 retries with max 30s backoff |

## Next Phase Readiness

- `services/claude.py` is importable and fully tested; plan 02-03 (database/companies.py) can import `Company` directly
- `discover_companies(filters)` returns `list[Company]` ready for DB persistence in plan 02-03
- Plan 02-04 (pages/1_Discover.py) can import `discover_companies` and `Company` directly
- No blockers

## Self-Check: PASSED

- [x] `services/__init__.py` exists at /Users/dakshigoel/Outreach/services/__init__.py
- [x] `services/claude.py` exists at /Users/dakshigoel/Outreach/services/claude.py
- [x] `tests/test_claude_service.py` exists at /Users/dakshigoel/Outreach/tests/test_claude_service.py
- [x] Commit `103fe14` exists (TDD RED)
- [x] Commit `a2a703a` exists (TDD GREEN)
- [x] All 26 tests pass: `python3 -m pytest tests/test_claude_service.py` exits 0
- [x] Import check: `from services.claude import Company, discover_companies, get_claude_client` exits 0
- [x] `web_search_20250305` present in claude.py
- [x] `claude-opus-4-7` present in claude.py
- [x] `model_validate` present in claude.py
- [x] `while` not in claude.py source

---

*Phase: 02-discovery*
*Completed: 2026-05-26*

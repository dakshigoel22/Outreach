# Phase 2: Discovery - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-25
**Phase:** 2-Discovery
**Areas discussed:** Claude output format, Result persistence, Duplicate detection

---

## Claude Output Format

| Option | Description | Selected |
|--------|-------------|----------|
| Ask Claude for JSON | Prompt instructs Claude to return a JSON array; validate with pydantic | ✓ |
| Parse Claude's prose response | Extract with regex/heuristics — fragile | |
| You decide | Leave to researcher/planner | |

**User's choice:** Ask Claude for JSON

---

| Option | Description | Selected |
|--------|-------------|----------|
| Block with spinner | Single call, batch results; matches discover_running flag | ✓ |
| Stream partial results | Companies appear one by one via streaming SDK | |

**User's choice:** Block with spinner

---

| Option | Description | Selected |
|--------|-------------|----------|
| Show whatever Claude found | Display all results even if 1–2; user decides to re-search | ✓ |
| Auto-retry with refined prompt | If results < N, Claude tries broader prompt automatically | |
| Show results + retry button | Display found + offer "Search again" button | |

**User's choice:** Show whatever Claude found

---

| Option | Description | Selected |
|--------|-------------|----------|
| 5–10 companies per search | Useful batch, low noise; tell Claude to target this range | ✓ |
| 10–20 companies per search | Broader but more hallucination risk | |
| You decide | Let planner tune based on web_search reliability | |

**User's choice:** 5–10 companies per search

---

## Result Persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Last results persist in session state | discover_results survives navigation until new search | ✓ |
| Blank page on return | Results clear on navigation | |
| Stored in DB with search history | Every search saved; adds a searches table | |

**User's choice:** Last search results still visible

---

| Option | Description | Selected |
|--------|-------------|----------|
| Persist filters in session state | Filter selections survive navigation | ✓ |
| Reset filters on each navigation | Cleaner state, user re-selects every time | |

**User's choice:** Yes, persist filters in session state

---

| Option | Description | Selected |
|--------|-------------|----------|
| Instructions + Discover button prominently | Show filters + clear CTA; no empty table | ✓ |
| Empty table/list placeholder | Show result container with "No results yet" | |

**User's choice:** Instructions + Discover button prominently

---

## Duplicate Detection

| Option | Description | Selected |
|--------|-------------|----------|
| Name match (case-insensitive) | Simple query on name field | |
| Website URL match | Match on website field | |
| Name OR URL match (either is a hit) | Check both fields; most thorough | ✓ |

**User's choice:** Name OR URL match (either is a hit)

---

| Option | Description | Selected |
|--------|-------------|----------|
| "Already saved" badge + disabled Save button | Green "Saved ✓" badge replaces Save button | ✓ |
| Grayed-out card | Entire card dims | |
| Save button replaced with "View in DB" link | Navigates to company record | |

**User's choice:** "Already saved" badge + disabled Save button

---

| Option | Description | Selected |
|--------|-------------|----------|
| Batch-check all companies after results load | Single SELECT with IN clause | ✓ |
| Per-card on render | N+1 queries — avoid | |
| Only on Save click | Check on save, error if duplicate | |

**User's choice:** Once after results load, batch-check all companies

---

## Claude's Discretion

- Exact prompt wording and system prompt structure for the web_search call
- Pydantic model field names and validation rules
- URL normalization strategy for duplicate URL matching
- Number of web_search calls per Discover run

## Deferred Ideas

None — discussion stayed within phase scope.

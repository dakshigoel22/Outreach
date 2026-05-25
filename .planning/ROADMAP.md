# Roadmap: Recruiter Outreach CRM

**Milestone:** v1 MVP
**Granularity:** Coarse
**Mode:** yolo
**Coverage:** 15/15 v1 requirements mapped

---

## Phases

- [ ] **Phase 1: Foundation** - Running Streamlit app with SQLite schema, correct connection patterns, session state, and My Profile page
- [ ] **Phase 2: Discovery** - Claude web_search pipeline discovers AI/ML startups and saves companies to DB
- [ ] **Phase 3: Contacts + Email** - Contact discovery and manual add, Claude email drafting, Gmail MCP send
- [ ] **Phase 4: Tracker + Dashboard** - Full pipeline tracker with inline edits, summary dashboard, and CSV export

---

## Phase Details

### Phase 1: Foundation
**Goal:** The app launches, all four DB tables exist with correct schema and WAL mode, session state is initialized on every page, and the user can fill in and save their profile — making every future email draft personalized from day one.
**Mode:** mvp
**Success Criteria**:
1. Running `streamlit run app.py` opens the multi-page app with sidebar nav showing Discover, Contacts, Draft Email, Tracker, Dashboard, and My Profile pages with no errors on first run.
2. The SQLite database is created automatically on first launch with all four tables (companies, contacts, emails, events) and WAL journal mode enabled.
3. Navigating directly to any page (including unvisited pages) produces no KeyError — session state keys are pre-initialized.
4. User can enter their name, school, degree, GPA, years of experience, skills, and bio on My Profile, save it, return later, and see the same values persisted.

**Requirements:** FOUND-01, FOUND-02, FOUND-03
**Plans**: TBD
**UI hint**: yes

---

### Phase 2: Discovery
**Goal:** User can set location/tier/role filters and trigger Claude to find real AI/ML startups via web search — with results appearing in-app and saveable to the DB in one click.
**Mode:** mvp
**Success Criteria**:
1. User selects filters (location, tier, role type) and clicks Discover — the app shows a spinner while Claude runs and displays company cards (name, funding stage, headcount, website, hiring roles) when done.
2. User can click "Save" on any result card and the company appears in the DB; already-saved companies are visually distinguished so the user does not save duplicates.
3. The Discover button is disabled while a search is in flight and re-enables after completion — no double-submit, no UI freeze.

**Requirements:** DISC-01, DISC-02
**Plans**: 5 plans

Plans:
- [ ] 02-01-PLAN.md — SDK upgrade (anthropic 0.28.0→0.104.1), pytest setup, .env.example, tests/ skeleton
- [ ] 02-02-PLAN.md — services/claude.py: Company model, discover_companies(), web_search integration
- [ ] 02-03-PLAN.md — database/companies.py: save_company(), get_saved_company_identifiers(); session state filter keys
- [ ] 02-04-PLAN.md — pages/1_Discover.py: full Discover page replacing placeholder
- [ ] 02-05-PLAN.md — tests/test_claude_service.py + tests/test_companies_db.py

---

### Phase 3: Contacts + Email
**Goal:** User can find recruiters per company (via Claude or manual entry), trigger a personalized email draft that uses their profile and the contact's context, review it in-app, and send it via Gmail MCP in one click.
**Mode:** mvp
**Success Criteria**:
1. User selects a saved company and clicks "Find Contacts" — Claude returns recruiter names, titles, and likely emails/LinkedIn; results appear alongside any manually added contacts.
2. User can manually add a contact (name, email, title, LinkedIn URL) to any saved company and it appears in the contact list immediately.
3. User selects a contact, clicks "Draft Email," and Claude returns a personalized under-150-word cold email that references the contact's role, the company's AI product, and the user's My Profile context.
4. User reviews the draft in-app, clicks Send, and the email is dispatched via Gmail MCP; contact status auto-updates to "Sent" only on confirmed success.

**Requirements:** CONT-01, CONT-02, EMAIL-01, EMAIL-02
**Plans**: TBD
**Research flag:** Verify Gmail MCP subprocess lifecycle in Streamlit, current `mcp` Python package API, and Gmail MCP server invocation contract at https://github.com/modelcontextprotocol/servers and https://pypi.org/project/mcp/ before writing `services/gmail_mcp.py`.
**UI hint**: yes

---

### Phase 4: Tracker + Dashboard
**Goal:** User has a single table to manage and update their full outreach pipeline, and a dashboard that shows whether their strategy is working — with CSV export for offline analysis.
**Mode:** mvp
**Success Criteria**:
1. Tracker page shows every contact in a table with color-coded status badges (Not Contacted / Drafted / Sent / Replied / Interview / Rejected); user can update any contact's status inline without leaving the page.
2. User can add or edit notes for any contact inline in the tracker table.
3. Dashboard shows summary metric cards (total contacts, emails sent, replies received, interviews scheduled, rejection rate) and user can filter the view by location, tier, AI focus, and status.
4. User can click Export and download the full filtered contact list as a CSV file.

**Requirements:** TRACK-01, TRACK-02, TRACK-03, DASH-01, DASH-02, DASH-03
**Plans**: TBD
**UI hint**: yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/0 | Not started | - |
| 2. Discovery | 0/5 | Planned | - |
| 3. Contacts + Email | 0/0 | Not started | - |
| 4. Tracker + Dashboard | 0/0 | Not started | - |

---

## Coverage Map

| Requirement | Phase |
|-------------|-------|
| FOUND-01 | Phase 1 |
| FOUND-02 | Phase 1 |
| FOUND-03 | Phase 1 |
| DISC-01 | Phase 2 |
| DISC-02 | Phase 2 |
| CONT-01 | Phase 3 |
| CONT-02 | Phase 3 |
| EMAIL-01 | Phase 3 |
| EMAIL-02 | Phase 3 |
| TRACK-01 | Phase 4 |
| TRACK-02 | Phase 4 |
| TRACK-03 | Phase 4 |
| DASH-01 | Phase 4 |
| DASH-02 | Phase 4 |
| DASH-03 | Phase 4 |

**Mapped:** 15/15 — no orphans.

---

*Created: 2026-05-24*

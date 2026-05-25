# Requirements: Recruiter Outreach CRM

**Defined:** 2026-05-24
**Core Value:** Find the right recruiters at the right companies and get a personalized email drafted and sent in as few clicks as possible.

## v1 Requirements

### Foundation

- [ ] **FOUND-01**: App initializes SQLite database with schema (companies, contacts, emails, statuses, events tables) on first run
- [ ] **FOUND-02**: App launches as multi-page Streamlit app with sidebar nav (Discover, Contacts, Draft Email, Tracker, Dashboard, My Profile)
- [ ] **FOUND-03**: User can fill in My Profile (name, school, degree, GPA, years of experience, skills, ML/NLP focus, bio) and settings are persisted to DB and used as context for all Claude email drafts

### Discovery

- [ ] **DISC-01**: User sets filters (location: NYC / Arlington VA / DC / SF; tier: Tier 2 / Tier 3 / Both; role type: internship / full-time / both) and Claude uses Anthropic web_search to find matching AI/ML startups — results show company name, funding stage, estimated headcount, website, and active hiring roles
- [ ] **DISC-02**: User can save any discovered company to the database with one click; already-saved companies are visually indicated in results

### Contacts

- [ ] **CONT-01**: User selects a saved company and triggers Claude to search for recruiters and hiring managers — results show name, title, and likely email/LinkedIn
- [ ] **CONT-02**: User can manually add a contact (name, email, title, LinkedIn URL) to any saved company

### Email

- [ ] **EMAIL-01**: User selects a contact and triggers Claude to draft a personalized cold email — Claude uses My Profile context, company details, and contact's role to write a specific, under-150-word email with a single clear ask
- [ ] **EMAIL-02**: User reviews the Claude-drafted email in-app and sends it via Gmail MCP with one click; contact status auto-updates to "Sent"

### Tracker

- [ ] **TRACK-01**: Tracker page shows every contact in a table with color-coded status badges: Not Contacted / Drafted / Sent / Replied / Interview / Rejected
- [ ] **TRACK-02**: User can update any contact's status inline in the tracker table
- [ ] **TRACK-03**: User can add or edit notes for any contact inline in the tracker table

### Dashboard

- [ ] **DASH-01**: Dashboard shows summary cards: total contacts found, emails sent, replies received, interviews scheduled, rejection rate
- [ ] **DASH-02**: User can filter the dashboard view by location, tier, AI focus, and status
- [ ] **DASH-03**: User can export the full filtered contact list to CSV

## v2 Requirements

### Contacts

- **CONT-V2-01**: Source badge on each contact row distinguishing AI-discovered vs. manually added contacts
- **CONT-V2-02**: Draft Email button is disabled (greyed out) when contact has no email address

### Email

- **EMAIL-V2-01**: Email type selector (internship / full-time / networking / follow-up) changes Claude's tone, length, and ask structure
- **EMAIL-V2-02**: Email history per contact — view all past drafts and sent emails

### Tracker

- **TRACK-V2-01**: Days-in-stage indicator — how many days since a contact's status last changed (surfaces stale leads)

### Dashboard

- **DASH-V2-01**: Reply rate broken down by company tier (Tier 2 vs. Tier 3) — shows where to focus outreach effort

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automated follow-up sequences | User decides when and how to follow up; automation risks appearing spammy |
| LinkedIn / Crunchbase API integrations | Discovery via Claude web_search only in v1; third-party API keys add setup friction |
| A/B testing email variants | Single-user app; sample size too small for meaningful testing |
| Tracking pixels / open rate tracking | Adds complexity, legal risk, not requested |
| Multi-user / team features | Single-user local app — shared state is out of scope |
| Cloud / hosted deployment | Runs locally; no auth, no server infra required |
| Rich text email editor | Claude drafts plain text; HTML email is anti-pattern for cold outreach |
| Calendar / interview scheduling integration | Out of scope; user handles scheduling externally |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Pending |
| FOUND-02 | Phase 1 | Pending |
| FOUND-03 | Phase 1 | Pending |
| DISC-01 | Phase 2 | Pending |
| DISC-02 | Phase 2 | Pending |
| CONT-01 | Phase 3 | Pending |
| CONT-02 | Phase 3 | Pending |
| EMAIL-01 | Phase 3 | Pending |
| EMAIL-02 | Phase 3 | Pending |
| TRACK-01 | Phase 4 | Pending |
| TRACK-02 | Phase 4 | Pending |
| TRACK-03 | Phase 4 | Pending |
| DASH-01 | Phase 4 | Pending |
| DASH-02 | Phase 4 | Pending |
| DASH-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-24*
*Last updated: 2026-05-24 after roadmap creation (4-phase structure)*

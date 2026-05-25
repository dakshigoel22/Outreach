# Recruiter Outreach CRM

## What This Is

A local Python + Streamlit web app for a UMD MS Data Science student (ML/NLP focus) to discover AI/ML startups at Tier 2/3 companies, find recruiter contacts, draft personalized cold emails via Claude, and track the full outreach pipeline. Runs fully locally against an SQLite database. No manual company entry — Claude does the discovery.

## Core Value

Find the right recruiters at the right companies and get a personalized email drafted and sent in as few clicks as possible.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **Discover**: Claude uses Anthropic web search to find AI/ML startups matching user-set filters (location: NYC, Arlington VA, DC, SF; tier: funding stage + headcount + must have active AI/ML product; role type)
- [ ] **Company detail**: Each discovered company shows team size, funding round, hiring roles, and website
- [ ] **Tier definition**: Tier 3 = Seed/Series A + 10–50 people; Tier 2 = Series B/C + 50–200 people; both must have an active AI/ML product
- [ ] **Contact discovery**: Claude searches for recruiters and hiring managers per company; results appear alongside any manually added contacts
- [ ] **Manual contact add**: User can add contacts (name, email, title, LinkedIn) from Apollo or LinkedIn with a source badge distinguishing manual vs. AI-discovered
- [ ] **My Profile settings page**: Dedicated page to enter/update background (MS Data Science @ UMD, 4.0 GPA, 4 years exp, TA, ML/NLP focus, resume text) — used as context for all email drafts
- [ ] **Email drafting**: User selects a contact + email type (internship / full-time / networking / follow-up), Claude writes a personalized cold email using My Profile context
- [ ] **Gmail MCP send**: Draft reviewed in-app, sent via Gmail MCP integration with one click
- [ ] **Tracker table**: Full table of every contact with color-coded status badges (Not Contacted → Drafted → Sent → Replied → Interview → Rejected), inline status update and notes
- [ ] **Dashboard**: Summary cards (contacts found, emails sent, replies, interviews, rejection rate); filterable by location, tier, AI focus, status; CSV export

### Out of Scope

- Email template library / rich text editor — Claude drafts are plain text; no complex formatting
- Multi-user / team features — single-user local app only
- Hosted/cloud deployment — runs locally; no auth, no server infra
- Automated follow-up scheduling — user decides when to follow up, app tracks it
- LinkedIn or Crunchbase API integrations — discovery is Claude web search only for v1

## Context

- **User**: UMD MS Data Science student, 4.0 GPA, 4 years of experience, TA, ML/NLP focus. Writing cold emails to recruiters and hiring managers at AI/ML startups.
- **Target companies**: Tier 2/3 AI/ML startups. Tier 3 = Seed/Series A, 10–50 people. Tier 2 = Series B/C, 50–200 people. Both require an active AI/ML product. Locations: NYC, Arlington VA, DC, SF.
- **Scale**: Ongoing outreach, no fixed ceiling — app must handle growing contact list gracefully.
- **Starting data**: Totally fresh — no existing contacts to import at launch.
- **Email sending**: Gmail MCP handles delivery; user reviews draft before send.
- **MVP priority**: Discover + Tracker are the highest-value features for week 1.
- **UI philosophy**: Functional and data-dense — tables, filters, quick inline edits. Speed over aesthetics.

## Constraints

- **Tech Stack**: Python, Streamlit, Anthropic SDK (with web_search tool), SQLite, pandas, Gmail MCP — no deviations without explicit decision
- **Local only**: No cloud infra, no hosted DB, no external auth
- **Claude as brain**: All discovery and drafting goes through Anthropic SDK; no third-party AI APIs
- **Gmail MCP**: Sending exclusively via MCP — no SMTP, no sendgrid

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Anthropic web search for discovery | Native to Anthropic SDK, no extra API keys, aligns with existing stack | — Pending |
| SQLite for persistence | Local-only app, pandas-friendly, zero-config | — Pending |
| Gmail MCP for sending | User requested; keeps sending in-app without SMTP complexity | — Pending |
| Source badges (AI vs. manual) on contacts | User mixes Claude-discovered and Apollo/LinkedIn contacts; needs to know provenance | — Pending |
| Tier definition = funding + headcount + AI product | Captures "big enough to hire, small enough to care" with AI specificity | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-24 after initialization*

# Feature Landscape: Recruiter Outreach CRM

**Domain:** Personal job-seeker outreach CRM — AI/ML startup discovery + cold email pipeline
**Researched:** 2026-05-24
**Confidence note:** Web access was blocked during research. All findings draw on training-data knowledge of Apollo.io, Lemlist, Outreach.io, Hunter.io, and job-seeker community behavior (r/cscareerquestions, Blind, LinkedIn), current as of August 2025. Confidence is MEDIUM across the board; validate competitor claims against current product before making them a hard requirement.

---

## What the Comparable Tools Do Well (Patterns to Borrow)

### Apollo.io — Contact Intelligence + Sequence Gating
Apollo's core value is that every contact has a completeness score before you reach out. It surfaces missing fields (no email, no direct phone) as blockers, not surprises. The pipeline view gates you: you cannot send a sequence step if required contact data is absent.

**Borrow:** Surface a "contact completeness" indicator on each row. If email is missing, the "Draft Email" button is disabled (or orange, not green). Don't let users draft emails they can't send.

### Lemlist — Liquid-Tag Personalization Variables
Lemlist popularized `{{first_name}}`, `{{company}}`, `{{icebreaker}}` slots filled per-recipient. The key insight is that the *template slot* is not the personalization — the *filled value* is. Their UX shows the preview with slots filled before send, not the raw template.

**Borrow:** Claude drafts the email, but surface a "preview as sent" view that shows what will actually land in the inbox — no raw `{{}}` tokens visible to the user at send time. Also: Claude should receive the contact's specific role title and company's current AI product (not just name) as inputs; generic name-drop is the failure mode.

### Hunter.io — Email Confidence Scoring
Hunter attaches a confidence percentage (0–100) to discovered email addresses based on pattern matching + verification signals. This prevents users from learning a bounce rate instead of a response rate.

**Borrow:** When Claude or the user adds an email, tag it with provenance (AI-discovered vs. manually added from Apollo/LinkedIn) and a simple quality signal: Verified / Unverified / Pattern-guess. Drive toward never sending to a Pattern-guess address without a manual confirmation step.

### Outreach.io — Pipeline Stage Transitions as Events
Outreach.io treats every stage change as a timestamped event, not just a field update. This enables "days in stage" calculations and surfaces stuck contacts ("been in Sent for 8 days, no reply").

**Borrow:** Store stage transitions in a separate events table, not just a current_status column. This costs almost nothing in SQLite and unlocks time-in-stage dashboards later without a schema migration.

### Streak (Gmail CRM) — In-Context Drafting
Streak lives inside Gmail. Its differentiator is that you never leave your drafting context to check pipeline status.

**Borrow:** In the Tracker table, clicking a contact row should open an inline panel (or sidebar) with the last email sent + current status — the user should not navigate away to see history.

---

## Table Stakes

Features users expect. Missing = product feels incomplete or broken vs. a spreadsheet.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Contact list with inline status update** | Core of any CRM; a spreadsheet does this for free | Low | Streamlit `st.data_editor` can handle inline edits natively |
| **Status stages: Not Contacted → Drafted → Sent → Replied → Interview → Rejected** | Every job-seeker spreadsheet has these columns | Low | Enum in SQLite; color-coded badges in UI |
| **Add contact manually** | Claude discovery will miss some; user will find contacts on Apollo/LinkedIn | Low | Name, email, title, company, LinkedIn URL, source badge |
| **View all contacts for a company** | Outreach is company-scoped; need to see all touchpoints per org | Low | Filter/group by company_id |
| **Draft email per contact** | The central action; without it the app is just a list | Medium | Requires My Profile context + contact data + email type input → Claude |
| **Send via Gmail** | Without send, user must copy-paste into Gmail manually — defeats the purpose | Medium | Gmail MCP; requires draft review step before send |
| **Mark email as sent after Gmail dispatch** | Pipeline integrity; status must update automatically on send | Low | Post-send hook updates status to "Sent" in SQLite |
| **Notes per contact** | Users always have context that doesn't fit a status field ("met at career fair", "referred by X") | Low | Freetext notes column; inline editable |
| **Filter tracker by status** | Can't manage 200 contacts without filtering | Low | Streamlit multiselect on status column |
| **My Profile settings** | Without user context, Claude drafts generic emails | Low | One-time setup; stored in SQLite; surfaced in every draft prompt |
| **Company list with tier badge** | Tier 2 vs. Tier 3 is core to the user's target strategy | Low | Derived from funding_stage + headcount; displayed as badge |
| **Discover companies via Claude** | The whole point of not being a spreadsheet; without this it's a fancy todo list | High | Anthropic SDK web_search; filter by location + tier + AI product requirement |

---

## Differentiators

Features that make this materially better than a spreadsheet or a generic CRM. Not expected, but valued — these are the "aha" moments.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Email type selector (Internship / Full-time / Networking / Follow-up)** | Changes Claude's tone, length, ask, and framing per type — one click reconfigures the entire draft strategy | Low | Enum passed to Claude prompt; dramatically changes output quality |
| **Source badge: AI-discovered vs. manually added** | User mixes Claude contacts with Apollo/LinkedIn contacts; provenance is trust signal | Low | badge column in contacts table; drives different display treatment |
| **Contact completeness gating** | "Draft Email" button disabled if email field is empty — surfaces the problem before wasting a Claude call | Low | Computed field; UI affordance only |
| **Inline company detail panel** (team size, funding round, active AI product, open roles) | Provides the context Claude needs for personalization without the user having to look it up separately | Medium | Stored at discovery time; refreshable per company |
| **Per-draft personalization inputs visible to user** | Show the user what signals Claude used (company AI product, contact role, user background) before they approve the draft — builds trust and allows correction | Low | Display the prompt context as a collapsible "What Claude knows" panel |
| **Days-in-stage indicator** | Surfaces stuck contacts ("Sent 9 days ago, no reply") without the user having to calculate | Medium | Requires events table (stage transitions with timestamps) not just current_status; computed at query time |
| **Dashboard: reply rate, interview conversion, rejection rate by tier** | Tells the user which tier/location/email type is actually working — lets them adjust strategy | Medium | Aggregation queries on events + contacts table; st.metric cards |
| **CSV export** | User may want to move data to a spreadsheet, share with a mentor, or back up | Low | pandas .to_csv(); one button |
| **Filter by location + tier + AI focus + status** | The user targets specific cities and tiers; cross-filtering these lets them run focused campaigns | Low | Streamlit multiselect filters; pandas query |
| **Follow-up flag** | "This contact replied but I haven't responded" or "It's been 7 days, I should follow up" — a simple boolean flag on a contact is enough | Low | Boolean column + filter; no scheduling logic required |
| **Email preview before send** | Shows the exact text that will be sent, post-Claude draft, before Gmail dispatch — prevents accidental sends of unedited drafts | Low | Streamlit text_area (editable) between draft and send |

---

## Anti-Features

Things to deliberately NOT build. Each is a scope creep trap that adds complexity without proportional value for a single-user local app.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Email template library / rich text editor** | Templates defeat the purpose of Claude personalization; rich text (HTML email) is overkill for cold outreach where plain text converts better | Claude drafts plain text; user edits in a plain textarea before send |
| **Automated follow-up scheduling / sequences** | Sequence logic (timers, conditional branches, A/B tests) is a product in itself; overkill for one person | User looks at days-in-stage, decides manually to follow up, drafts a follow-up email with "follow-up" type selector |
| **Email open/click tracking pixels** | Requires a hosted endpoint to receive beacon callbacks; incompatible with local-only constraint; also increasingly blocked by email clients | Track reply (manual status update to "Replied") as the signal that matters |
| **LinkedIn API / Crunchbase API integrations** | API costs, OAuth complexity, rate limits — adds infra burden; Claude web search covers the discovery use case | Claude web_search handles discovery for v1; manual add handles the rest |
| **Multi-user / team features** | Single user; any sharing, permissions, or collaboration model is pure complexity | Local SQLite, no auth, no sharing |
| **Cloud/hosted deployment** | Adds auth, infra, cost, security surface — none of which serves a solo local app | Local Streamlit on localhost; no deployment |
| **A/B testing email variants** | Sample size (one person's outreach) is statistically meaningless for A/B testing | Track what email type and tier correlate with replies; that's enough signal |
| **Contact deduplication / merge UI** | Complex to build correctly; edge cases multiply fast | Prevent duplicates at insert time (unique constraint on email); surface a warning if user tries to add a duplicate |
| **CRM import (CSV upload of existing contacts)** | User starts fresh — no existing contacts to import; building import logic is pure overhead | Manual add + Claude discovery covers the ingestion need |
| **Calendar integration / interview scheduling** | Interview scheduling is the company's job (Calendly, Greenhouse); tracking that an interview exists is enough | Status badge "Interview" is sufficient; no calendar sync needed |
| **Browser extension / email sidebar** | Building a Chrome extension adds a separate release artifact, manifest complexity, and a different runtime | Streamlit UI is the single surface; acceptable for a focused local tool |
| **AI-generated company scoring / ranking** | Ranking which company to email next sounds useful but produces false precision; the user's tier filter is already a ranking signal | Tier badge + days-in-stage + status filter gives enough prioritization signal |

---

## Feature Dependencies

```
My Profile settings
    └── Email drafting (Claude needs profile context as input)
            └── Gmail send (can only send what's been drafted)
                    └── Status: Drafted → Sent (auto-update on send)

Company discovery
    └── Company detail (funding, headcount, AI product, roles)
            └── Contact discovery per company
                    └── Contact completeness gating (email present?)
                            └── Email drafting (requires email + role + company detail)

Status stage transitions (events table)
    └── Days-in-stage indicator (derived from event timestamps)
    └── Dashboard metrics (reply rate, conversion — derived from stage counts)

Filter (location + tier + status)
    └── Tracker table view (all filters apply to same table)
    └── Dashboard (same filters applied to aggregate view)
```

---

## MVP Recommendation

The project already has clear MVP priority (Discover + Tracker). This research validates and sharpens it:

**Build first (Week 1 — MVP):**
1. My Profile settings page — unblocks all drafting
2. Tracker table with status badges + inline edit + notes — the daily-use surface
3. Company discovery via Claude — core differentiator over a spreadsheet
4. Contact add (manual) with source badge — needed before discovery is reliable
5. Email drafting with email type selector — the "aha" moment

**Build second (Week 2 — Core loop complete):**
6. Gmail MCP send + auto status update to Sent
7. Company detail panel (surfaced at discovery time)
8. Contact discovery per company via Claude
9. Email preview before send
10. Filter by status / tier / location

**Build third (Week 3+ — Insight layer):**
11. Events table + days-in-stage indicator
12. Dashboard with reply rate, conversion by tier
13. Follow-up flag
14. CSV export
15. Contact completeness gating (UI affordance)

**Defer indefinitely:**
- Everything in the anti-features list above

---

## What Job Seekers Actually Track (Spreadsheet Baseline)

Based on community patterns from r/cscareerquestions, Blind, and LinkedIn discussions (MEDIUM confidence, training data):

Standard columns in a job-seeker outreach spreadsheet:
- Company name
- Role / title targeted
- Recruiter name + email
- Date of first contact
- Status (the stage enum above)
- Last action taken
- Next action / follow-up date
- Notes (what was said, referral source, interview feedback)
- Response (yes/no/ghosted)
- Source (LinkedIn, referral, job board, cold outreach)

What they wish they had (expressed pain points):
- "I can't remember what I said to this person" — email history per contact
- "I don't know which companies I've already emailed" — company-level deduplication
- "My emails feel copy-pasted and I know it" — real personalization, not just name-swap
- "I don't know if cold emailing is even working" — reply rate signal
- "I keep forgetting to follow up" — days-since-sent visibility

This app directly addresses all five. The events table + days-in-stage + email type selector are direct answers to the top pain points.

---

## What Makes Cold Email Personalization Work

Distilled from practitioner writing and research on cold email response rates (MEDIUM confidence, training data):

**Works:**
- Specific reference to the company's actual AI product or recent work ("your NLP pipeline for claims processing" not "your AI initiatives")
- Role-match: connecting the user's specific skills to the specific role or team, not generic "I love ML"
- Short and specific ask: "15 minutes to learn about your ML team's work" converts better than "explore opportunities"
- First line that isn't about the sender: lead with the company/role observation, not "My name is X and I'm a student at Y"
- Plain text: HTML formatting signals mass outreach; plain text signals individual effort

**Fails:**
- Name-drop personalization only (`Hi {{first_name}}`) — every tool does this; it no longer signals human effort
- Long paragraphs about GPA and coursework — the contact doesn't have time; lead with relevance
- Asking for a job in the first email — converts worse than asking for a conversation
- Generic subject lines ("Interested in opportunities at [Company]") — low open rate
- Sending to generic info@ or careers@ instead of a named person

**Implication for Claude prompt design:**
Claude should receive: contact's role title + company's specific AI product description + user's most relevant project/skill match + email type (internship/full-time/networking/follow-up). The prompt should instruct Claude to lead with a company-specific observation, keep it under 150 words, use plain text, and end with a single low-friction ask.

---

## Sources

- PROJECT.md project context (local file, current)
- Training-data knowledge of Apollo.io, Lemlist, Outreach.io, Hunter.io, Streak CRM feature sets as of August 2025 — MEDIUM confidence; product features may have changed
- Community-reported job-seeker spreadsheet patterns (r/cscareerquestions, Blind, LinkedIn) — MEDIUM confidence
- Cold email effectiveness research (Woodpecker, Lemlist, Reply.io published studies) — MEDIUM confidence; verify specific statistics before citing
- WebSearch and WebFetch were blocked in this research session; all findings are from training data

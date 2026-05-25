<!-- GSD:project-start source:PROJECT.md -->
## Project

**Recruiter Outreach CRM**

A local Python + Streamlit web app for a UMD MS Data Science student (ML/NLP focus) to discover AI/ML startups at Tier 2/3 companies, find recruiter contacts, draft personalized cold emails via Claude, and track the full outreach pipeline. Runs fully locally against an SQLite database. No manual company entry — Claude does the discovery.

**Core Value:** Find the right recruiters at the right companies and get a personalized email drafted and sent in as few clicks as possible.

### Constraints

- **Tech Stack**: Python, Streamlit, Anthropic SDK (with web_search tool), SQLite, pandas, Gmail MCP — no deviations without explicit decision
- **Local only**: No cloud infra, no hosted DB, no external auth
- **Claude as brain**: All discovery and drafting goes through Anthropic SDK; no third-party AI APIs
- **Gmail MCP**: Sending exclusively via MCP — no SMTP, no sendgrid
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Framework
| Technology | Version (verify) | Purpose | Why |
|------------|-----------------|---------|-----|
| Python | 3.11+ | Runtime | 3.11 brings meaningful perf gains over 3.10; 3.12 is stable but some ML deps lag; 3.11 is the safe current sweet spot. |
| Streamlit | 1.35+ | UI layer | Purpose-built for data apps; `st.data_editor` (stable since 1.23) covers inline CRM editing without custom JS; multipage via `pages/` directory is first-class. |
| Anthropic Python SDK | 0.28+ | Claude API client | Official SDK; provides typed client, streaming, tool_use block handling, and the `web_search` tool integration point. |
| SQLite (stdlib) | 3.x (bundled) | Persistence | Zero-config, file-based, ships with Python. Right-sized for a single-user local app with a few thousand rows. |
| pandas | 2.1+ | Data manipulation | Required by `st.data_editor`; 2.x uses Copy-on-Write by default which avoids silent mutation bugs common in 1.x. |
### Database Layer
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| sqlite3 (stdlib) | bundled | DB driver | No install needed; works fine for all CRUD at this scale. |
| SQLAlchemy Core (optional) | 2.0+ | Connection management | If you hit Streamlit thread-safety issues (see Pitfalls), `SQLAlchemy` with `StaticPool` or `NullPool` solves them cleanly. Do NOT use the ORM — Core + raw SQL is lighter and keeps pandas integration simple. |
### AI Integration
| Technology | Version (verify) | Purpose | Why |
|------------|-----------------|---------|-----|
| anthropic | 0.28+ | Claude API calls | Official client; the only supported way to call Anthropic APIs. |
### Email Integration
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Gmail MCP server | community | Email sending | User-mandated; keeps sending in-app without SMTP complexity. |
- Google OAuth 2.0 credentials (client ID + client secret from Google Cloud Console)
- A `credentials.json` file downloaded from your GCP project
- First-run browser OAuth flow to generate `token.json` (refresh token persists locally)
- Gmail API must be enabled in the GCP project
- `@modelcontextprotocol/server-gmail` (Node.js, from the official MCP examples repo) — requires Node.js runtime alongside Python
- Community Python ports exist but are less mature
### Supporting Libraries
| Library | Version (verify) | Purpose | When to Use |
|---------|-----------------|---------|-------------|
| `st-aggrid` | 0.3.x | Advanced data grid | If `st.data_editor` proves insufficient (complex column types, row grouping). Heavy JS dependency — prefer native `st.data_editor` first and only add this if blocked. |
| `pydantic` | 2.x | Data validation | Validate Claude's JSON output before writing to SQLite. Claude web_search responses are unstructured; always parse/validate before persistence. |
| `python-dotenv` | 1.0+ | Env var management | Store `ANTHROPIC_API_KEY` in `.env`; never hardcode. |
| `tenacity` | 8.x | Retry logic | Wrap Anthropic API calls with exponential backoff; web_search calls can hit rate limits. |
| `httpx` | 0.27+ | HTTP client | Anthropic SDK dependency; do not install separately unless needed for direct requests. |
- `streamlit-aggrid` unless `st.data_editor` is genuinely insufficient — it adds a JS build dependency and breaks on Streamlit version updates frequently.
- `SQLAlchemy ORM` — heavy abstraction unnecessary for this app; Core or raw sqlite3 is enough.
- `aiosqlite` — async SQLite driver; not needed since Streamlit runs synchronously per rerun.
- Any additional AI API clients (OpenAI, etc.) — project constraint is Anthropic-only.
## Streamlit Patterns for a Data-Dense CRM
### Multi-page Architecture
### Inline Editing with `st.data_editor`
# Load from SQLite
# Render editable table
# Detect changes and persist
### Session State for CRUD
# Initialize once
### Status Badges (Color-Coded)
## SQLite + pandas Thread Safety in Streamlit
## Schema Design (Starter)
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| UI framework | Streamlit | Dash (Plotly) | Dash requires more boilerplate for simple CRUD; Streamlit is faster for data-dense local apps |
| UI framework | Streamlit | FastAPI + React | Massive overkill for single-user local app; no browser state needed |
| DB driver | sqlite3 + st.cache_resource | SQLAlchemy ORM | ORM adds abstraction with no benefit at this scale; raw SQL + pandas is simpler |
| Data grid | st.data_editor | st-aggrid | st-aggrid has JS dependency and version fragility; st.data_editor is sufficient for this use case |
| Email delivery | Gmail MCP | smtplib / sendgrid | Project constraint; MCP keeps sending in-app and is user-mandated |
| AI SDK | anthropic | openai / litellm | Project constraint; Anthropic SDK is the only supported client |
| Retry logic | tenacity | manual retry loops | tenacity provides exponential backoff, jitter, and decorators in 3 lines |
## Installation
# Core app
# MCP client for Gmail integration
# Optional: only add if st.data_editor is insufficient
# pip install streamlit-aggrid
# Install Node.js (via nvm recommended)
# Install the Gmail MCP server
## Version Verification Checklist
| Item | Where to verify | Why critical |
|------|----------------|--------------|
| Anthropic `web_search` tool type string | `https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search-tool` | Type string is versioned and changes |
| Current Claude model names | `https://docs.anthropic.com/en/docs/about-claude/models` | Model IDs change with new releases |
| Streamlit `st.data_editor` column config API | `https://docs.streamlit.io/develop/api-reference/data/st.data_editor` | Column config options evolve |
| `mcp` Python package API | `https://pypi.org/project/mcp/` | Package is relatively new; API may have changed |
| Gmail MCP server package name | `https://github.com/modelcontextprotocol/servers` | Package name and install method may differ |
## Sources
- Anthropic SDK docs: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search-tool
- Anthropic model list: https://docs.anthropic.com/en/docs/about-claude/models
- Streamlit data_editor: https://docs.streamlit.io/develop/api-reference/data/st.data_editor
- Streamlit multipage: https://docs.streamlit.io/develop/concepts/multipage-apps
- Streamlit cache_resource: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- MCP server registry: https://github.com/modelcontextprotocol/servers
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

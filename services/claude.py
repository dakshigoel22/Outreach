"""Claude API service for Recruiter Outreach CRM.

Provides the Company pydantic model, Anthropic client singleton, and the
discover_companies() function that calls Claude with the web_search tool
to find AI/ML startups matching user-specified filters.

Usage:
    from services.claude import discover_companies, Company

    results = discover_companies({"location": "NYC", "tier": "Both", "role_type": "Both"})
    for company in results:
        print(company.name, company.website)
"""
import json
import re
from typing import Optional

import streamlit as st
from anthropic import Anthropic, APITimeoutError, RateLimitError
from pydantic import BaseModel, ValidationError, field_validator
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class Company(BaseModel):
    """Validated company record from Claude's web_search discovery response.

    All fields except name are optional — Claude may not always find complete data.
    field_validators normalize website URLs and coerce hiring_roles to a list.
    """

    name: str
    funding_stage: Optional[str] = None
    headcount: Optional[str] = None
    website: Optional[str] = None
    ai_focus: Optional[str] = None
    location: Optional[str] = None
    tier: Optional[str] = None
    hiring_roles: list[str] = []

    @field_validator("website", mode="before")
    @classmethod
    def normalize_website(cls, v):
        """Strip trailing slash; prepend https:// if no scheme is present."""
        if v is None:
            return None
        v = str(v).rstrip("/")
        if v and not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v

    @field_validator("hiring_roles", mode="before")
    @classmethod
    def coerce_roles(cls, v):
        """Coerce string → [string] and None → []; pass lists through unchanged."""
        if isinstance(v, str):
            return [v] if v else []
        if v is None:
            return []
        return list(v)


SYSTEM_PROMPT = """You are a company research assistant for a UMD MS Data Science student
targeting AI/ML startup roles.

When asked to find companies, respond with ONLY a valid JSON array of company objects.
No prose before or after the JSON array.

Each object must have these exact fields (use null if unknown):
{
  "name": "Company Name",
  "funding_stage": "Series A",
  "headcount": "50-200",
  "website": "https://example.com",
  "ai_focus": "NLP and computer vision applications",
  "location": "NYC",
  "tier": "Tier 2",
  "hiring_roles": ["ML Engineer Intern", "Data Scientist"]
}

Tier 2 = companies with 200-2000 employees, established product, Series B+.
Tier 3 = companies with 10-200 employees, early stage, Seed/Series A.
Only return companies actively hiring for AI/ML roles."""


@st.cache_resource
def get_claude_client() -> Anthropic:
    """Cached Anthropic client singleton.

    Decorated with @st.cache_resource so it is created once per Streamlit
    session rather than on every page rerun. Reads ANTHROPIC_API_KEY from env
    (loaded via python-dotenv in app.py).
    """
    return Anthropic()


@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _call_claude_api(client: Anthropic, user_message: str):
    """Call Claude with the web_search server tool. Retries on rate limits/timeouts.

    Uses web_search_20250305 (stable tool type, verified 2026-05-25).
    Uses claude-opus-4-7 (confirmed in official web_search docs examples).
    max_uses=5 caps cost; 5 web searches is sufficient for 5-10 companies.

    IMPORTANT: This is a single blocking call. web_search is a server-side tool;
    the API handles the search loop internally. No multi-turn polling needed.
    """
    return client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 5,
        }],
    )


def _build_user_message(filters: dict) -> str:
    """Build the user-turn message from filter dict values.

    Args:
        filters: Dict with optional keys "location", "tier", "role_type".
                 Defaults: location="NYC", tier="Both", role_type="Both".

    Returns:
        A user-turn message string requesting JSON company results.
    """
    location = filters.get("location", "NYC")
    tier = filters.get("tier", "Both")
    role_type = filters.get("role_type", "Both")

    tier_desc = "Tier 2 or Tier 3" if tier == "Both" else tier
    role_desc = "internship and full-time" if role_type == "Both" else role_type

    return (
        f"Find 5 to 10 real AI/ML startups in {location} that are {tier_desc} "
        f"companies currently hiring for {role_desc} positions. "
        f"Use web search for current information. Return ONLY a JSON array."
    )


def _extract_companies(response) -> list[Company]:
    """Extract and validate Company objects from a Claude API response.

    Collects all text blocks from the mixed content block response, joins them,
    finds the first JSON array with re.search, parses it, and validates each
    item through Company.model_validate(). Invalid items are skipped silently.

    Args:
        response: A claude messages.create() response object.

    Returns:
        A list of validated Company objects (may be empty).
    """
    text_parts = [b.text for b in response.content if b.type == "text"]
    full_text = "\n".join(text_parts)

    match = re.search(r'\[.*\]', full_text, re.DOTALL)
    if not match:
        return []

    try:
        raw = json.loads(match.group())
    except json.JSONDecodeError:
        return []

    result = []
    for item in raw:
        try:
            result.append(Company.model_validate(item))
        except ValidationError:
            continue
    return result


def discover_companies(filters: dict) -> list[Company]:
    """Discover AI/ML startups via Claude web_search.

    Single blocking call — no polling loop. Retries on rate limits/timeouts
    (handled by @retry on _call_claude_api). The caller (pages/1_Discover.py)
    wraps this in st.spinner and catches exceptions for st.error display.

    Args:
        filters: Dict with keys "location", "tier", "role_type".

    Returns:
        A list of validated Company objects. May be empty if Claude found
        nothing or if JSON extraction/validation failed entirely.
    """
    client = get_claude_client()
    user_message = _build_user_message(filters)
    response = _call_claude_api(client, user_message)
    return _extract_companies(response)


__all__ = ["Company", "discover_companies", "get_claude_client"]

"""Tests for services/claude.py — Company model and extraction helpers.

Covers Company pydantic model validators and _extract_companies() logic.
No API calls are made — all Claude interactions are mocked via SimpleNamespace.
"""
import json
import os
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from services.claude import Company, _extract_companies, _build_user_message


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_text_response(text: str) -> SimpleNamespace:
    """Build a mock Claude response with mixed content blocks.

    Mirrors the real web_search response structure: a server_tool_use block,
    a web_search_tool_result block, and a text block. Only the text block is
    consumed by _extract_companies().
    """
    return SimpleNamespace(content=[
        SimpleNamespace(type="server_tool_use", id="x"),
        SimpleNamespace(type="web_search_tool_result", content=[]),
        SimpleNamespace(type="text", text=text),
    ])


# ---------------------------------------------------------------------------
# Company model — name validation
# ---------------------------------------------------------------------------

def test_company_name_required():
    """Company() without name raises ValidationError."""
    with pytest.raises(ValidationError):
        Company()


def test_company_defaults():
    """Company(name='X') has all optional fields None and hiring_roles=[]."""
    c = Company(name="X")
    assert c.funding_stage is None
    assert c.headcount is None
    assert c.website is None
    assert c.ai_focus is None
    assert c.location is None
    assert c.tier is None
    assert c.hiring_roles == []


# ---------------------------------------------------------------------------
# Company model — website normalization
# ---------------------------------------------------------------------------

def test_website_adds_https():
    """Company(name='X', website='example.com').website == 'https://example.com'."""
    c = Company(name="X", website="example.com")
    assert c.website == "https://example.com"


def test_website_strips_trailing_slash():
    """Company(name='X', website='https://acme.com/').website == 'https://acme.com'."""
    c = Company(name="X", website="https://acme.com/")
    assert c.website == "https://acme.com"


def test_website_none_stays_none():
    """Company(name='X', website=None).website is None."""
    c = Company(name="X", website=None)
    assert c.website is None


# ---------------------------------------------------------------------------
# Company model — hiring_roles coercion
# ---------------------------------------------------------------------------

def test_hiring_roles_string_coercion():
    """Company(name='X', hiring_roles='ML').hiring_roles == ['ML']."""
    c = Company(name="X", hiring_roles="ML")
    assert c.hiring_roles == ["ML"]


def test_hiring_roles_none_coercion():
    """Company(name='X', hiring_roles=None).hiring_roles == []."""
    c = Company(name="X", hiring_roles=None)
    assert c.hiring_roles == []


def test_hiring_roles_empty_string_coercion():
    """Company(name='X', hiring_roles='').hiring_roles == []."""
    c = Company(name="X", hiring_roles="")
    assert c.hiring_roles == []


# ---------------------------------------------------------------------------
# _extract_companies — core extraction tests
# ---------------------------------------------------------------------------

def test_extract_companies_valid_json():
    """_extract_companies with mock response containing valid JSON array returns list[Company]."""
    data = [{"name": "Acme AI", "hiring_roles": ["ML Engineer"]}]
    response = make_text_response(json.dumps(data))
    result = _extract_companies(response)
    assert len(result) == 1
    assert result[0].name == "Acme AI"
    assert isinstance(result[0], Company)


def test_extract_companies_json_in_prose():
    """_extract_companies handles response where text starts with prose before JSON."""
    data = [{"name": "StartupX", "hiring_roles": []}]
    text = "Here are the results:\n" + json.dumps(data) + "\nHope this helps."
    response = make_text_response(text)
    result = _extract_companies(response)
    assert len(result) == 1
    assert result[0].name == "StartupX"


def test_extract_companies_no_json():
    """_extract_companies returns [] when no JSON array in text blocks."""
    response = make_text_response("No companies found.")
    result = _extract_companies(response)
    assert result == []


def test_extract_companies_ignores_non_text_blocks():
    """_extract_companies skips server_tool_use and web_search_tool_result blocks."""
    data = [{"name": "TechCo", "hiring_roles": ["Data Scientist"]}]
    # The make_text_response helper already includes non-text blocks before the text block.
    response = make_text_response(json.dumps(data))
    result = _extract_companies(response)
    assert len(result) == 1
    assert result[0].name == "TechCo"


def test_extract_companies_skips_invalid_items():
    """One malformed dict in JSON array (missing 'name') is skipped; valid items returned."""
    data = [
        {"name": "ValidCo", "hiring_roles": ["ML Engineer"]},
        {"hiring_roles": ["NLP"]},   # missing required 'name' — skipped
        {"name": "AnotherCo"},
    ]
    response = make_text_response(json.dumps(data))
    result = _extract_companies(response)
    assert len(result) == 2
    names = [c.name for c in result]
    assert "ValidCo" in names
    assert "AnotherCo" in names


# ---------------------------------------------------------------------------
# Additional coverage — _build_user_message and module exports
# ---------------------------------------------------------------------------

def test_build_user_message_both_defaults():
    """Filters with Both tier and Both role_type produce expected message content."""
    msg = _build_user_message({"location": "NYC", "tier": "Both", "role_type": "Both"})
    assert "NYC" in msg
    assert "Tier 2 or Tier 3" in msg
    assert "internship and full-time" in msg


def test_build_user_message_specific_tier():
    """Tier 2 filter produces 'Tier 2' not 'Tier 2 or Tier 3'."""
    msg = _build_user_message({"location": "SF", "tier": "Tier 2", "role_type": "Full-time"})
    assert "Tier 2" in msg
    assert "Tier 2 or Tier 3" not in msg


def test_build_user_message_default_fallbacks():
    """Empty filters dict uses defaults: NYC, Both tier, Both role_type."""
    msg = _build_user_message({})
    assert "NYC" in msg


def test_module_all_exports():
    """services.claude __all__ includes Company, discover_companies, get_claude_client."""
    import services.claude as m
    assert "Company" in m.__all__
    assert "discover_companies" in m.__all__
    assert "get_claude_client" in m.__all__


def test_no_while_loop_in_source():
    """services/claude.py must NOT contain a while loop (no multi-turn polling pattern)."""
    src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "services", "claude.py")
    with open(src_path) as f:
        src = f.read()
    assert "while " not in src, "Found 'while' loop in claude.py — forbidden per anti-pattern docs"


def test_web_search_tool_type_present():
    """services/claude.py must contain the verified web_search_20250305 type string."""
    src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "services", "claude.py")
    with open(src_path) as f:
        src = f.read()
    assert "web_search_20250305" in src


def test_model_validate_used():
    """services/claude.py must use model_validate (pydantic v2 API, not parse_obj)."""
    src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "services", "claude.py")
    with open(src_path) as f:
        src = f.read()
    assert "model_validate" in src

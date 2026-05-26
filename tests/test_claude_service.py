"""Tests for services/claude.py — Company model and extraction helpers.

TDD RED: These tests are written before the implementation exists.
They cover the Company pydantic model validators and _extract_companies() logic.
No API calls are made — all Claude interactions are mocked.
"""
import json
import unittest
from unittest.mock import MagicMock, patch


class TestCompanyModel(unittest.TestCase):
    """Tests for the Company pydantic BaseModel."""

    def test_name_required(self):
        """Company() with no name raises ValidationError."""
        from pydantic import ValidationError
        from services.claude import Company
        with self.assertRaises(ValidationError):
            Company()

    def test_name_only_valid(self):
        """Company(name='Acme') validates successfully."""
        from services.claude import Company
        c = Company(name="Acme")
        self.assertEqual(c.name, "Acme")

    def test_website_none_stays_none(self):
        """Company(name='Acme', website=None) keeps website as None."""
        from services.claude import Company
        c = Company(name="Acme", website=None)
        self.assertIsNone(c.website)

    def test_website_no_scheme_gets_https(self):
        """Company(name='Acme', website='example.com') normalizes to 'https://example.com'."""
        from services.claude import Company
        c = Company(name="Acme", website="example.com")
        self.assertEqual(c.website, "https://example.com")

    def test_website_trailing_slash_stripped(self):
        """Company(name='Acme', website='https://acme.com/') strips trailing slash."""
        from services.claude import Company
        c = Company(name="Acme", website="https://acme.com/")
        self.assertEqual(c.website, "https://acme.com")

    def test_website_http_kept(self):
        """Company with http:// prefix keeps it (no forced upgrade to https)."""
        from services.claude import Company
        c = Company(name="Acme", website="http://acme.com")
        self.assertEqual(c.website, "http://acme.com")

    def test_hiring_roles_string_coerced_to_list(self):
        """Company(hiring_roles='ML Engineer') coerces to ['ML Engineer']."""
        from services.claude import Company
        c = Company(name="Acme", hiring_roles="ML Engineer")
        self.assertEqual(c.hiring_roles, ["ML Engineer"])

    def test_hiring_roles_none_becomes_empty_list(self):
        """Company(hiring_roles=None) coerces to []."""
        from services.claude import Company
        c = Company(name="Acme", hiring_roles=None)
        self.assertEqual(c.hiring_roles, [])

    def test_hiring_roles_list_unchanged(self):
        """Company(hiring_roles=['A', 'B']) keeps list unchanged."""
        from services.claude import Company
        c = Company(name="Acme", hiring_roles=["A", "B"])
        self.assertEqual(c.hiring_roles, ["A", "B"])

    def test_hiring_roles_empty_string_becomes_empty_list(self):
        """Company(hiring_roles='') coerces to []."""
        from services.claude import Company
        c = Company(name="Acme", hiring_roles="")
        self.assertEqual(c.hiring_roles, [])

    def test_optional_fields_default_none(self):
        """All optional fields default to None."""
        from services.claude import Company
        c = Company(name="Acme")
        self.assertIsNone(c.funding_stage)
        self.assertIsNone(c.headcount)
        self.assertIsNone(c.website)
        self.assertIsNone(c.ai_focus)
        self.assertIsNone(c.location)
        self.assertIsNone(c.tier)

    def test_hiring_roles_defaults_empty_list(self):
        """hiring_roles defaults to [] when not provided."""
        from services.claude import Company
        c = Company(name="Acme")
        self.assertEqual(c.hiring_roles, [])


class TestExtractCompanies(unittest.TestCase):
    """Tests for _extract_companies() — JSON extraction from mock Claude response."""

    def _make_response(self, blocks):
        """Build a mock response object with content blocks."""
        response = MagicMock()
        content_blocks = []
        for b in blocks:
            block = MagicMock()
            block.type = b["type"]
            if b["type"] == "text":
                block.text = b["text"]
            content_blocks.append(block)
        response.content = content_blocks
        return response

    def test_extracts_companies_from_pure_json(self):
        """_extract_companies() returns Company list when response is pure JSON array."""
        from services.claude import _extract_companies
        data = [{"name": "Acme AI", "hiring_roles": ["ML Engineer"]}]
        response = self._make_response([{"type": "text", "text": json.dumps(data)}])
        result = _extract_companies(response)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Acme AI")

    def test_extracts_json_after_prose(self):
        """_extract_companies() handles Claude adding prose before the JSON array."""
        from services.claude import _extract_companies
        data = [{"name": "StartupX", "hiring_roles": []}]
        text = "Here are the companies I found:\n" + json.dumps(data)
        response = self._make_response([{"type": "text", "text": text}])
        result = _extract_companies(response)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "StartupX")

    def test_skips_server_tool_use_blocks(self):
        """_extract_companies() ignores server_tool_use blocks."""
        from services.claude import _extract_companies
        data = [{"name": "TechCo", "hiring_roles": ["Data Scientist"]}]
        response = self._make_response([
            {"type": "server_tool_use"},
            {"type": "web_search_tool_result"},
            {"type": "text", "text": json.dumps(data)},
        ])
        result = _extract_companies(response)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "TechCo")

    def test_returns_empty_list_when_no_json_array(self):
        """_extract_companies() returns [] when response has no JSON array."""
        from services.claude import _extract_companies
        response = self._make_response([{"type": "text", "text": "No companies found."}])
        result = _extract_companies(response)
        self.assertEqual(result, [])

    def test_returns_empty_list_on_invalid_json(self):
        """_extract_companies() returns [] when JSON is malformed."""
        from services.claude import _extract_companies
        response = self._make_response([{"type": "text", "text": "[not valid json{"}])
        result = _extract_companies(response)
        self.assertEqual(result, [])

    def test_skips_invalid_items_in_batch(self):
        """_extract_companies() skips items that fail pydantic validation, returns valid ones."""
        from services.claude import _extract_companies
        data = [
            {"name": "ValidCo", "hiring_roles": ["ML Engineer"]},
            {"hiring_roles": ["NLP"]},  # missing required 'name' field
            {"name": "AnotherCo"},
        ]
        response = self._make_response([{"type": "text", "text": json.dumps(data)}])
        result = _extract_companies(response)
        self.assertEqual(len(result), 2)
        names = [c.name for c in result]
        self.assertIn("ValidCo", names)
        self.assertIn("AnotherCo", names)

    def test_empty_response_content(self):
        """_extract_companies() returns [] when response has no content blocks."""
        from services.claude import _extract_companies
        response = self._make_response([])
        result = _extract_companies(response)
        self.assertEqual(result, [])


class TestBuildUserMessage(unittest.TestCase):
    """Tests for _build_user_message() filter dict → prompt string."""

    def test_both_tier_and_role(self):
        """Filters with Both tier and Both role_type produce expected message."""
        from services.claude import _build_user_message
        msg = _build_user_message({"location": "NYC", "tier": "Both", "role_type": "Both"})
        self.assertIn("NYC", msg)
        self.assertIn("Tier 2 or Tier 3", msg)
        self.assertIn("internship and full-time", msg)

    def test_specific_tier(self):
        """Tier 2 filter produces 'Tier 2' not 'Tier 2 or Tier 3'."""
        from services.claude import _build_user_message
        msg = _build_user_message({"location": "SF", "tier": "Tier 2", "role_type": "Full-time"})
        self.assertIn("Tier 2", msg)
        self.assertNotIn("Tier 2 or Tier 3", msg)

    def test_default_fallbacks(self):
        """Empty filters dict uses defaults: NYC, Both tier, Both role_type."""
        from services.claude import _build_user_message
        msg = _build_user_message({})
        self.assertIn("NYC", msg)


class TestModuleExports(unittest.TestCase):
    """Tests that public API is exported correctly."""

    def test_all_exports(self):
        """services.claude __all__ includes Company, discover_companies, get_claude_client."""
        import services.claude as m
        self.assertIn("Company", m.__all__)
        self.assertIn("discover_companies", m.__all__)
        self.assertIn("get_claude_client", m.__all__)

    def test_no_while_loop_in_source(self):
        """services/claude.py must NOT contain a while loop (no multi-turn pattern)."""
        import os
        src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "services", "claude.py")
        with open(src_path) as f:
            src = f.read()
        self.assertNotIn("while ", src, "Found 'while' loop in claude.py — forbidden per anti-pattern docs")

    def test_web_search_tool_type_present(self):
        """services/claude.py must contain the verified web_search_20250305 type string."""
        import os
        src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "services", "claude.py")
        with open(src_path) as f:
            src = f.read()
        self.assertIn("web_search_20250305", src)

    def test_model_validate_used(self):
        """services/claude.py must use model_validate (pydantic v2 API, not parse_obj)."""
        import os
        src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "services", "claude.py")
        with open(src_path) as f:
            src = f.read()
        self.assertIn("model_validate", src)


if __name__ == "__main__":
    unittest.main()

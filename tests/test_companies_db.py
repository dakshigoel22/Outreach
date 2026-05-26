"""Tests for database/companies.py — save_company and get_saved_company_identifiers.

All tests use an in-memory SQLite fixture (monkeypatched) — no writes to outreach.db.
The autouse fixture creates a fresh in-memory DB per test function.
"""
import sqlite3

import pytest

import database.companies as companies_module
from services.claude import Company
from database.companies import save_company, get_saved_company_identifiers


_CREATE_TABLE_SQL = """
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    funding_stage TEXT,
    headcount TEXT,
    website TEXT,
    ai_focus TEXT,
    location TEXT,
    tier TEXT,
    hiring_roles TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch):
    """Create a fresh in-memory SQLite DB per test and monkeypatch get_connection.

    Monkeypatches database.companies.get_connection (the name bound in the
    companies module by the 'from database.connection import get_connection'
    import) so that save_company() and get_saved_company_identifiers() use
    in-memory SQLite instead of the real outreach.db.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE_SQL)
    conn.commit()
    monkeypatch.setattr(companies_module, "get_connection", lambda: conn)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# get_saved_company_identifiers — empty state
# ---------------------------------------------------------------------------

def test_get_identifiers_empty(in_memory_db):
    """Fresh in-memory DB returns (set(), set())."""
    names, urls = get_saved_company_identifiers()
    assert names == set()
    assert urls == set()


# ---------------------------------------------------------------------------
# save_company — basic insertion
# ---------------------------------------------------------------------------

def test_save_company_inserts_row(in_memory_db):
    """save_company(c) then get_identifiers returns name in names set."""
    c = Company(name="Acme AI")
    save_company(c)
    names, urls = get_saved_company_identifiers()
    assert "acme ai" in names


def test_save_company_name_lowercased(in_memory_db):
    """get_identifiers returns lowercase version of saved name."""
    c = Company(name="UPPER AI")
    save_company(c)
    names, _ = get_saved_company_identifiers()
    assert "upper ai" in names
    assert "UPPER AI" not in names


def test_save_company_url_normalized(in_memory_db):
    """website 'https://Acme.com/' stored; get_identifiers returns 'https://acme.com' in urls set."""
    # Company validator strips trailing slash: 'https://Acme.com/' -> 'https://Acme.com'
    # get_identifiers lowercases: 'https://acme.com'
    c = Company(name="Acme", website="https://Acme.com/")
    save_company(c)
    _, urls = get_saved_company_identifiers()
    assert "https://acme.com" in urls


# ---------------------------------------------------------------------------
# save_company — hiring_roles serialization
# ---------------------------------------------------------------------------

def test_save_company_serializes_hiring_roles(in_memory_db):
    """save_company with hiring_roles=['ML','NLP']; raw DB row has hiring_roles=='ML,NLP'."""
    c = Company(name="Test", hiring_roles=["ML", "NLP"])
    save_company(c)
    row = in_memory_db.execute("SELECT hiring_roles FROM companies").fetchone()
    assert row["hiring_roles"] == "ML,NLP"


def test_save_company_empty_roles_is_none(in_memory_db):
    """save_company with hiring_roles=[]; raw DB row has hiring_roles IS NULL."""
    c = Company(name="Test")
    save_company(c)
    row = in_memory_db.execute("SELECT hiring_roles FROM companies").fetchone()
    assert row["hiring_roles"] is None


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def test_duplicate_detection_by_name(in_memory_db):
    """Company already in DB -> name.lower() in names set -> True."""
    c = Company(name="Startup Corp")
    save_company(c)
    names, _ = get_saved_company_identifiers()
    assert "startup corp" in names


def test_duplicate_detection_by_url(in_memory_db):
    """Company already in DB with url -> url.rstrip('/').lower() in urls set -> True."""
    c = Company(name="AnotherCo", website="https://another.com/")
    save_company(c)
    _, urls = get_saved_company_identifiers()
    # Company validator strips trailing slash -> stored as 'https://another.com'
    # get_identifiers lowercases it -> 'https://another.com'
    assert "https://another.com" in urls


def test_url_excluded_when_none(in_memory_db):
    """Row with website=None does not cause KeyError; urls set does not contain None."""
    c = Company(name="NoWebsite")
    save_company(c)
    names, urls = get_saved_company_identifiers()
    assert None not in urls
    assert "nowebsite" in names

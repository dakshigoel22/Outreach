"""Database schema initialization for Outreach CRM.

Creates all five tables with IF NOT EXISTS guards — safe to call on every startup.
Uses executescript() with literal SQL only — no f-string interpolation (T-01-01).
"""
from database.connection import get_connection

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS companies (
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
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES companies(id),
    name TEXT NOT NULL,
    title TEXT,
    email TEXT,
    linkedin_url TEXT,
    source TEXT DEFAULT 'manual',
    status TEXT DEFAULT 'Not Contacted',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER REFERENCES contacts(id),
    subject TEXT,
    body TEXT,
    status TEXT DEFAULT 'Draft',
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER REFERENCES contacts(id),
    event_type TEXT,
    detail TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    full_name TEXT,
    school TEXT,
    degree TEXT,
    gpa REAL,
    years_experience INTEGER,
    skills TEXT,
    ml_nlp_focus TEXT,
    bio TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db() -> None:
    """Initialize all database tables.

    Idempotent — uses IF NOT EXISTS so repeated calls are safe.
    Executes a single executescript() call with literal SQL only.
    """
    conn = get_connection()
    conn.executescript(_SCHEMA_SQL)
    conn.commit()


__all__ = ["init_db"]

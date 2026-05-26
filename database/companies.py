"""Company persistence and duplicate detection for Outreach CRM."""
from database.connection import get_connection
from services.claude import Company


def save_company(company: Company) -> None:
    """Insert a company.

    Caller is responsible for duplicate check before calling
    (badge hides Save button for already-saved companies).

    All 8 fields are inserted via ? parameterized placeholders — no f-string SQL.
    hiring_roles is serialized as a comma-joined TEXT value (SQLite has no list type).
    """
    conn = get_connection()
    hiring_roles_text = ",".join(company.hiring_roles) if company.hiring_roles else None
    conn.execute(
        "INSERT INTO companies "
        "(name, funding_stage, headcount, website, ai_focus, location, tier, hiring_roles) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            company.name,
            company.funding_stage,
            company.headcount,
            company.website,
            company.ai_focus,
            company.location,
            company.tier,
            hiring_roles_text,
        ),
    )
    conn.commit()


def get_saved_company_identifiers() -> tuple[set[str], set[str]]:
    """Return (lowercase_names, normalized_urls) sets for O(1) duplicate detection (per D-08, D-09).

    Names are lowercased. URLs are lowercased and trailing slashes stripped.
    Rows with NULL name or NULL website are excluded from the respective sets.
    """
    conn = get_connection()
    cursor = conn.execute("SELECT name, website FROM companies")
    rows = cursor.fetchall()
    names = {row["name"].lower() for row in rows if row["name"]}
    urls = {row["website"].rstrip("/").lower() for row in rows if row["website"]}
    return (names, urls)


__all__ = ["save_company", "get_saved_company_identifiers"]

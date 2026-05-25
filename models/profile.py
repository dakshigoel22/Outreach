"""Profile DB model for Outreach CRM.

Provides get_profile() and save_profile() for the singleton profile row (id=1).
Uses parameterized queries only — no f-string SQL interpolation (T-02-01).
"""
from database.connection import get_connection


def get_profile() -> dict:
    """Return the profile row as a dict, or {} if no profile has been saved yet.

    Uses the singleton row pattern: SELECT WHERE id=1.
    Returns {} (empty dict) if no row found — callers handle empty state.
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM profile WHERE id = ?", (1,)).fetchone()
    if row is None:
        return {}
    return dict(row)


def save_profile(data: dict) -> None:
    """Upsert the singleton profile row (id=1) with the provided data.

    Uses INSERT OR REPLACE with positional ? placeholders only — no f-strings.
    Calls conn.commit() after every write.

    Args:
        data: dict with keys full_name, school, degree, gpa, years_experience,
              skills, ml_nlp_focus, bio. Missing keys use safe defaults.
    """
    conn = get_connection()
    conn.execute(
        """
        INSERT OR REPLACE INTO profile
            (id, full_name, school, degree, gpa, years_experience, skills, ml_nlp_focus, bio, updated_at)
        VALUES
            (1, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            data["full_name"],
            data["school"],
            data.get("degree", ""),
            data.get("gpa", 0.0),
            data.get("years_experience", 0),
            data.get("skills", ""),
            data.get("ml_nlp_focus", ""),
            data.get("bio", ""),
        ),
    )
    conn.commit()


__all__ = ["get_profile", "save_profile"]

"""SQLite connection layer for Outreach CRM.

Provides a single cached connection with WAL mode enabled.
No SQLAlchemy, no aiosqlite — plain sqlite3 stdlib only.
"""
import os
import pathlib
import sqlite3

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Validate DB_PATH is not an absolute path outside cwd (T-01-03: path traversal mitigation)
_raw_db_path = os.getenv("DB_PATH", "outreach.db")
_db_path_obj = pathlib.Path(_raw_db_path)
if _db_path_obj.is_absolute():
    _cwd = pathlib.Path.cwd()
    try:
        _db_path_obj.resolve().relative_to(_cwd.resolve())
    except ValueError as _exc:
        raise ValueError(
            f"DB_PATH '{_raw_db_path}' is an absolute path outside the project directory. "
            "Set DB_PATH to a relative path (e.g. 'outreach.db')."
        ) from _exc

DB_PATH: pathlib.Path = _db_path_obj


@st.cache_resource
def get_connection() -> sqlite3.Connection:
    """Return a cached SQLite connection with WAL mode and foreign keys enabled.

    Decorated with @st.cache_resource so a single connection is shared across
    all Streamlit reruns in the same process. check_same_thread=False is required
    because Streamlit may call this from multiple threads.
    """
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


__all__ = ["get_connection", "DB_PATH"]

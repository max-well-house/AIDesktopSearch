"""SQLite connection helpers — stdlib only (#39)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from db.schema import SCHEMA_SQL, SCHEMA_VERSION

# backend/db/connection.py → backend/ → repo root
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

DEFAULT_DB_PATH = _PROJECT_ROOT / "data" / "index.db"


def get_db_path() -> Path:
    """Resolve DB path. Override with AIDESKTOP_DB (absolute or relative)."""
    override = os.environ.get("AIDESKTOP_DB")
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_DB_PATH


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> Path:
    """Create the DB file if needed and apply the schema foundation."""
    path = db_path or get_db_path()
    with connect(path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.execute(f"PRAGMA user_version = {int(SCHEMA_VERSION)}")
        conn.commit()
    return path

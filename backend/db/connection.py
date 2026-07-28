"""SQLite connection helpers (#39 / #67)."""

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
    # Embed worker + search/status share this file — avoid long lock freezes (#85).
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    # sqlite-vec is per-connection; soft-fail inside load helper (#67).
    try:
        from embeddings.vec import load_sqlite_vec

        load_sqlite_vec(conn)
    except Exception:
        pass
    return conn


def init_db(db_path: Path | None = None) -> Path:
    """Create the DB file if needed and apply the schema foundation."""
    path = db_path or get_db_path()
    with connect(path) as conn:
        conn.executescript(SCHEMA_SQL)
        row = conn.execute("PRAGMA user_version").fetchone()
        current = int(row[0]) if row is not None else 0
        if current < 4:
            cols = {
                r[1]
                for r in conn.execute("PRAGMA table_info(roots)").fetchall()
            }
            if "auto_watch" not in cols:
                conn.execute(
                    "ALTER TABLE roots ADD COLUMN auto_watch INTEGER NOT NULL DEFAULT 1"
                )
        conn.execute(f"PRAGMA user_version = {int(SCHEMA_VERSION)}")
        try:
            from embeddings.vec import ensure_vec_schema

            ensure_vec_schema(conn)
        except Exception:
            # Classic search must still work if the extension is missing.
            pass
        conn.commit()
    return path

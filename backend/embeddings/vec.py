"""Load sqlite-vec into a SQLite connection (Decision #008 / #67).

Soft-fail: missing package, disabled load_extension, or DLL errors must not
break classic search. Extension state is per-connection — call load on every
new connection.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)

# nomic-embed-text default dimension — locked into vec0 schema for v0.7.
VEC_DIMENSION = 768


def load_sqlite_vec(conn: sqlite3.Connection) -> dict[str, Any]:
    """
    Try to load sqlite-vec onto ``conn``.

    Returns a status dict:
      available: bool
      version: str | None
      note: str | None
      dimension: int
    """
    status: dict[str, Any] = {
        "available": False,
        "version": None,
        "note": None,
        "dimension": VEC_DIMENSION,
    }
    try:
        import sqlite_vec
    except ImportError:
        status["note"] = "sqlite-vec package not installed"
        return status

    try:
        conn.enable_load_extension(True)
    except AttributeError:
        status["note"] = "this Python build cannot load SQLite extensions"
        return status
    except sqlite3.Error as exc:
        status["note"] = f"enable_load_extension failed: {exc}"
        return status

    try:
        sqlite_vec.load(conn)
        row = conn.execute("SELECT vec_version()").fetchone()
        version = row[0] if row else None
        status["available"] = True
        status["version"] = str(version) if version is not None else None
        status["note"] = None
    except (sqlite3.Error, OSError, AttributeError) as exc:
        logger.warning("sqlite-vec load failed: %s", exc)
        status["note"] = f"sqlite-vec load failed: {exc}"
    finally:
        try:
            conn.enable_load_extension(False)
        except (AttributeError, sqlite3.Error):
            pass

    return status


def ensure_vec_schema(conn: sqlite3.Connection) -> bool:
    """
    Create vec0 virtual table + cleanup trigger when the extension is loaded.

    Returns True if vec tables are ready.
    """
    loaded = load_sqlite_vec(conn)
    if not loaded["available"]:
        return False

    dim = int(loaded["dimension"])
    conn.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
            chunk_id INTEGER PRIMARY KEY,
            embedding float[{dim}] distance_metric=cosine
        )
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS embedding_chunks_ad_vec
        AFTER DELETE ON embedding_chunks
        BEGIN
            DELETE FROM vec_chunks WHERE chunk_id = old.id;
        END
        """
    )
    return True

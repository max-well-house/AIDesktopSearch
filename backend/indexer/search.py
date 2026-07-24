"""Classic filename search against SQLite (#42)."""

from __future__ import annotations

from db import connect

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def _escape_like(value: str) -> str:
    """Escape LIKE metacharacters so user input is matched literally."""
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def search_filenames(query: str, *, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """
    Case-insensitive substring match on files.name.

    Empty/whitespace query returns []. Results prefer prefix hits, then
    alphabetical name. Cap with limit (clamped 1..MAX_LIMIT).
    """
    q = (query or "").strip()
    if not q:
        return []

    capped = max(1, min(int(limit), MAX_LIMIT))
    pattern = f"%{_escape_like(q)}%"
    prefix = f"{_escape_like(q)}%"

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, path, name, extension, size, mtime, root_id
            FROM files
            WHERE name LIKE ? ESCAPE '\\' COLLATE NOCASE
            ORDER BY
              CASE
                WHEN name LIKE ? ESCAPE '\\' COLLATE NOCASE THEN 0
                ELSE 1
              END,
              name COLLATE NOCASE
            LIMIT ?
            """,
            (pattern, prefix, capped),
        ).fetchall()

    return [
        {
            "id": int(row["id"]),
            "path": row["path"],
            "name": row["name"],
            "extension": row["extension"],
            "size": int(row["size"]) if row["size"] is not None else None,
            "mtime": float(row["mtime"]) if row["mtime"] is not None else None,
            "root_id": int(row["root_id"]) if row["root_id"] is not None else None,
        }
        for row in rows
    ]

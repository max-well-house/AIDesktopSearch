"""Persist file metadata into SQLite (#41)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from db import connect


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_root(path: Path) -> int:
    """Insert or fetch a corpus root; return roots.id."""
    resolved = str(path.resolve())
    now = _utc_now()
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM roots WHERE path = ?", (resolved,)
        ).fetchone()
        if row:
            return int(row["id"])
        cur = conn.execute(
            "INSERT INTO roots (path, added_at, last_scan_at) VALUES (?, ?, ?)",
            (resolved, now, None),
        )
        conn.commit()
        return int(cur.lastrowid)


def upsert_file(
    *,
    root_id: int,
    path: Path,
    indexed_at: str | None = None,
) -> None:
    """Insert or replace one file row by absolute path."""
    resolved = path.resolve()
    stat = resolved.stat()
    name = resolved.name
    extension = resolved.suffix.lstrip(".").lower() or None
    when = indexed_at or _utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO files (root_id, path, name, extension, size, mtime, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                root_id = excluded.root_id,
                name = excluded.name,
                extension = excluded.extension,
                size = excluded.size,
                mtime = excluded.mtime,
                indexed_at = excluded.indexed_at
            """,
            (
                root_id,
                str(resolved),
                name,
                extension,
                int(stat.st_size),
                float(stat.st_mtime),
                when,
            ),
        )
        conn.commit()


def replace_root_files(
    root_id: int,
    file_paths: list[Path],
    *,
    indexed_at: str | None = None,
) -> tuple[int, int]:
    """
    Upsert all scanned files for a root and delete rows no longer on disk.

    Returns (upserted_count, removed_count).
    """
    when = indexed_at or _utc_now()
    seen: list[str] = []
    upserted = 0

    with connect() as conn:
        for raw in file_paths:
            resolved = raw.resolve()
            try:
                stat = resolved.stat()
            except OSError:
                continue
            path_str = str(resolved)
            seen.append(path_str)
            conn.execute(
                """
                INSERT INTO files (root_id, path, name, extension, size, mtime, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    root_id = excluded.root_id,
                    name = excluded.name,
                    extension = excluded.extension,
                    size = excluded.size,
                    mtime = excluded.mtime,
                    indexed_at = excluded.indexed_at
                """,
                (
                    root_id,
                    path_str,
                    resolved.name,
                    resolved.suffix.lstrip(".").lower() or None,
                    int(stat.st_size),
                    float(stat.st_mtime),
                    when,
                ),
            )
            upserted += 1

        if seen:
            placeholders = ",".join("?" * len(seen))
            cur = conn.execute(
                f"""
                DELETE FROM files
                WHERE root_id = ?
                  AND path NOT IN ({placeholders})
                """,
                (root_id, *seen),
            )
        else:
            cur = conn.execute(
                "DELETE FROM files WHERE root_id = ?", (root_id,)
            )
        removed = int(cur.rowcount or 0)

        conn.execute(
            "UPDATE roots SET last_scan_at = ? WHERE id = ?",
            (when, root_id),
        )
        conn.commit()

    return upserted, removed


def index_status() -> dict:
    with connect() as conn:
        file_count = int(
            conn.execute("SELECT COUNT(*) AS c FROM files").fetchone()["c"]
        )
        root_count = int(
            conn.execute("SELECT COUNT(*) AS c FROM roots").fetchone()["c"]
        )
        last = conn.execute(
            "SELECT MAX(indexed_at) AS last_indexed_at FROM files"
        ).fetchone()["last_indexed_at"]
        roots = [
            {
                "id": int(row["id"]),
                "path": row["path"],
                "last_scan_at": row["last_scan_at"],
                "file_count": int(
                    conn.execute(
                        "SELECT COUNT(*) AS c FROM files WHERE root_id = ?",
                        (row["id"],),
                    ).fetchone()["c"]
                ),
            }
            for row in conn.execute(
                "SELECT id, path, last_scan_at FROM roots ORDER BY id"
            )
        ]
    return {
        "file_count": file_count,
        "root_count": root_count,
        "last_indexed_at": last,
        "roots": roots,
    }

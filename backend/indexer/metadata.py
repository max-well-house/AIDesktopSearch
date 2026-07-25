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
    """Insert or replace one file row by absolute path; sync PDF content when applicable."""
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

    from indexer.content import maybe_sync_path

    maybe_sync_path(resolved)


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

    from indexer.content import sync_pdfs_for_root

    sync_pdfs_for_root(root_id)

    return upserted, removed


def _abs_path_str(path: Path | str) -> str:
    """Absolute path string; works for deleted paths when parents still exist."""
    p = Path(path)
    try:
        return str(p.resolve())
    except OSError:
        return str(p)


def _path_under_prefix(path_str: str, prefix: str) -> bool:
    """True if path_str is prefix or a child (either OS separator)."""
    if path_str == prefix:
        return True
    sep = "\\" if "\\" in prefix or (len(prefix) >= 2 and prefix[1] == ":") else "/"
    # Accept both separators for robustness.
    return (
        path_str.startswith(prefix + "\\")
        or path_str.startswith(prefix + "/")
        or path_str.startswith(prefix + sep)
    )


def delete_file(path: Path | str) -> int:
    """Remove one file row by absolute path. Returns rows deleted."""
    path_str = _abs_path_str(path)
    with connect() as conn:
        cur = conn.execute("DELETE FROM files WHERE path = ?", (path_str,))
        conn.commit()
        return int(cur.rowcount or 0)


def delete_files_under_prefix(root_id: int, dir_path: Path | str) -> int:
    """Delete all file rows under a directory prefix for a root (dir delete/move)."""
    prefix = _abs_path_str(dir_path).rstrip("\\/")
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, path FROM files WHERE root_id = ?",
            (root_id,),
        ).fetchall()
        ids = [int(r["id"]) for r in rows if _path_under_prefix(r["path"], prefix)]
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        cur = conn.execute(
            f"DELETE FROM files WHERE id IN ({placeholders})",
            ids,
        )
        conn.commit()
        return int(cur.rowcount or 0)


def rename_file(old_path: Path | str, new_path: Path | str, *, root_id: int) -> None:
    """Update path/name for a rename, or delete+upsert if UNIQUE conflicts."""
    old_str = _abs_path_str(old_path)
    new_resolved = Path(new_path)
    try:
        new_resolved = new_resolved.resolve()
    except OSError:
        pass
    new_str = str(new_resolved)

    when = _utc_now()
    name = new_resolved.name
    extension = new_resolved.suffix.lstrip(".").lower() or None
    size: int | None = None
    mtime: float | None = None
    if new_resolved.is_file():
        try:
            st = new_resolved.stat()
            size = int(st.st_size)
            mtime = float(st.st_mtime)
        except OSError:
            pass

    with connect() as conn:
        existing_new = conn.execute(
            "SELECT id FROM files WHERE path = ?", (new_str,)
        ).fetchone()
        if existing_new and old_str != new_str:
            conn.execute("DELETE FROM files WHERE path = ?", (old_str,))
            conn.execute(
                """
                UPDATE files SET
                    root_id = ?,
                    name = ?,
                    extension = ?,
                    size = COALESCE(?, size),
                    mtime = COALESCE(?, mtime),
                    indexed_at = ?
                WHERE path = ?
                """,
                (root_id, name, extension, size, mtime, when, new_str),
            )
        else:
            cur = conn.execute(
                """
                UPDATE files SET
                    root_id = ?,
                    path = ?,
                    name = ?,
                    extension = ?,
                    size = COALESCE(?, size),
                    mtime = COALESCE(?, mtime),
                    indexed_at = ?
                WHERE path = ?
                """,
                (root_id, new_str, name, extension, size, mtime, when, old_str),
            )
            if int(cur.rowcount or 0) == 0 and new_resolved.is_file():
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
                        new_str,
                        name,
                        extension,
                        size or 0,
                        mtime or 0.0,
                        when,
                    ),
                )
        conn.commit()

    from indexer.content import maybe_sync_path

    maybe_sync_path(new_str)


def rename_files_under_prefix(
    root_id: int, old_dir: Path | str, new_dir: Path | str
) -> int:
    """Rewrite path prefixes when a directory is moved. Returns rows updated."""
    old_prefix = _abs_path_str(old_dir).rstrip("\\/")
    new_prefix = _abs_path_str(new_dir).rstrip("\\/")
    when = _utc_now()
    touched: list[str] = []
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, path FROM files WHERE root_id = ?",
            (root_id,),
        ).fetchall()
        updated = 0
        for row in rows:
            old_file = row["path"]
            if not _path_under_prefix(old_file, old_prefix):
                continue
            suffix = old_file[len(old_prefix) :]
            new_file = new_prefix + suffix
            new_name = Path(new_file).name
            extension = Path(new_file).suffix.lstrip(".").lower() or None
            # Drop colliding destination rows first.
            conn.execute(
                "DELETE FROM files WHERE path = ? AND id != ?",
                (new_file, row["id"]),
            )
            conn.execute(
                """
                UPDATE files SET path = ?, name = ?, extension = ?, indexed_at = ?
                WHERE id = ?
                """,
                (new_file, new_name, extension, when, row["id"]),
            )
            touched.append(new_file)
            updated += 1
        conn.commit()

    from indexer.content import maybe_sync_path

    for path_str in touched:
        maybe_sync_path(path_str)

    return updated


def vacuum_index() -> None:
    """Rewrite the DB file to reclaim free pages after deletes (#40).

    Not a forensic secure erase — that remains a later privacy feature.
    """
    with connect() as conn:
        conn.execute("VACUUM")


def delete_root(root_id: int) -> dict | None:
    """
    Remove a corpus root and its file rows (ON DELETE CASCADE), then VACUUM.

    Returns a summary dict, or None if the root id does not exist.
    """
    with connect() as conn:
        row = conn.execute(
            "SELECT id, path FROM roots WHERE id = ?", (root_id,)
        ).fetchone()
        if not row:
            return None
        file_count = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM files WHERE root_id = ?",
                (root_id,),
            ).fetchone()["c"]
        )
        conn.execute("DELETE FROM roots WHERE id = ?", (root_id,))
        conn.commit()
        path = row["path"]

    # Outside the delete transaction — SQLite forbids VACUUM mid-transaction.
    vacuum_index()

    status = index_status()
    return {
        "root_id": root_id,
        "root_path": path,
        "files_removed": file_count,
        "file_count": status["file_count"],
        "root_count": status["root_count"],
        "last_indexed_at": status["last_indexed_at"],
    }


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

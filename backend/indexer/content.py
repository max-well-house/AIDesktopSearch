"""Persist document text into SQLite FTS (#55 / #62 / Decision #006 / #007)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from db import connect
from indexer.extract import CONTENT_EXTENSIONS, extract_for_path

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _abs_path_str(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve())
    except OSError:
        return str(p)


def clear_file_content(file_id: int) -> None:
    """Remove FTS pages, file_content, and embedding chunks for a file id."""
    with connect() as conn:
        conn.execute("DELETE FROM file_pages_fts WHERE file_id = ?", (file_id,))
        conn.execute("DELETE FROM file_content WHERE file_id = ?", (file_id,))
        conn.commit()
    try:
        from embeddings.store import clear_file_embeddings

        clear_file_embeddings(file_id)
    except Exception:
        with connect() as conn:
            conn.execute("DELETE FROM embedding_chunks WHERE file_id = ?", (file_id,))
            conn.commit()


def sync_file_content(file_id: int, path: Path | str, mtime: float | None) -> None:
    """
    Extract document text and replace FTS + file_content for file_id.

    Skips work when mtime_at_parse already matches mtime.
    Never raises for extract failures (soft-fail into status/warning).
    """
    path_str = _abs_path_str(path)
    with connect() as conn:
        row = conn.execute(
            "SELECT mtime_at_parse FROM file_content WHERE file_id = ?",
            (file_id,),
        ).fetchone()
        if (
            row is not None
            and mtime is not None
            and row["mtime_at_parse"] is not None
            and float(row["mtime_at_parse"]) == float(mtime)
        ):
            return

    try:
        extracted = extract_for_path(path_str)
    except Exception:  # noqa: BLE001
        logger.exception("unexpected extract failure for %s", path_str)
        extracted = None

    when = _utc_now()
    with connect() as conn:
        conn.execute("DELETE FROM file_pages_fts WHERE file_id = ?", (file_id,))

        if extracted is None:
            conn.execute(
                """
                INSERT INTO file_content (
                    file_id, parser, parser_version, page_count, mtime_at_parse,
                    status, warning, parsed_at
                ) VALUES (?, 'unknown', NULL, NULL, ?, 'error', ?, ?)
                ON CONFLICT(file_id) DO UPDATE SET
                    parser = excluded.parser,
                    parser_version = excluded.parser_version,
                    page_count = excluded.page_count,
                    mtime_at_parse = excluded.mtime_at_parse,
                    status = excluded.status,
                    warning = excluded.warning,
                    parsed_at = excluded.parsed_at
                """,
                (file_id, mtime, "unexpected extract failure", when),
            )
            conn.commit()
            try:
                from embeddings.store import clear_file_embeddings

                clear_file_embeddings(file_id)
            except Exception:
                pass
            return

        warning = "; ".join(extracted.warnings) if extracted.warnings else None
        fts_rows = [
            (text, file_id, int(page))
            for page, text in extracted.pages
            if (text or "").strip()
        ]
        if fts_rows:
            conn.executemany(
                """
                INSERT INTO file_pages_fts (text, file_id, page)
                VALUES (?, ?, ?)
                """,
                fts_rows,
            )

        conn.execute(
            """
            INSERT INTO file_content (
                file_id, parser, parser_version, page_count, mtime_at_parse,
                status, warning, parsed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_id) DO UPDATE SET
                parser = excluded.parser,
                parser_version = excluded.parser_version,
                page_count = excluded.page_count,
                mtime_at_parse = excluded.mtime_at_parse,
                status = excluded.status,
                warning = excluded.warning,
                parsed_at = excluded.parsed_at
            """,
            (
                file_id,
                extracted.parser,
                extracted.parser_version,
                extracted.page_count,
                mtime,
                extracted.status,
                warning,
                when,
            ),
        )
        conn.commit()

    # No extractable text → drop stale vectors. Embedding is opt-in (#122):
    # content sync leaves pending files; Start embedding / backfill enqueues.
    if not fts_rows:
        try:
            from embeddings.store import clear_file_embeddings

            clear_file_embeddings(file_id)
        except Exception:
            pass


# Backward-compatible alias (#55 / tests / bench).
sync_pdf_content = sync_file_content


def maybe_sync_path(path: Path | str) -> None:
    """
    Sync or clear content for a path already present in ``files``.

    Content-eligible extensions → sync_file_content; others with leftover
    content → clear.
    """
    path_str = _abs_path_str(path)
    with connect() as conn:
        row = conn.execute(
            "SELECT id, extension, mtime FROM files WHERE path = ?",
            (path_str,),
        ).fetchone()
        if not row:
            return
        file_id = int(row["id"])
        extension = (row["extension"] or "").lower()
        mtime = float(row["mtime"]) if row["mtime"] is not None else None
        has_content = conn.execute(
            "SELECT 1 FROM file_content WHERE file_id = ?",
            (file_id,),
        ).fetchone()

    if extension in CONTENT_EXTENSIONS:
        sync_file_content(file_id, path_str, mtime)
    elif has_content:
        clear_file_content(file_id)


def sync_content_for_root(root_id: int) -> None:
    """
    After a bulk replace_root_files, sync every content-eligible file under the root.

    Also clears leftover ``file_content`` / FTS for files under the root whose
    extension is no longer content-eligible (e.g. extension flip on rescan).

    Single-threaded and lean (#58): one file at a time, cooperative yield
    between files so the OS can schedule other work (search / future Ollama).
    """
    placeholders = ", ".join("?" for _ in CONTENT_EXTENSIONS) or "NULL"
    ext_params = tuple(sorted(CONTENT_EXTENSIONS))
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id, path, mtime FROM files
            WHERE root_id = ? AND lower(extension) IN ({placeholders})
            """,
            (root_id, *ext_params),
        ).fetchall()
        stale = conn.execute(
            f"""
            SELECT fc.file_id
            FROM file_content AS fc
            JOIN files AS f ON f.id = fc.file_id
            WHERE f.root_id = ?
              AND lower(COALESCE(f.extension, '')) NOT IN ({placeholders})
            """,
            (root_id, *ext_params),
        ).fetchall()

    for row in stale:
        try:
            clear_file_content(int(row["file_id"]))
        except Exception:  # noqa: BLE001
            logger.exception("content clear failed for file_id=%s", row["file_id"])

    total = len(rows)
    for i, row in enumerate(rows):
        try:
            mtime = float(row["mtime"]) if row["mtime"] is not None else None
            sync_file_content(int(row["id"]), row["path"], mtime)
        except Exception:  # noqa: BLE001
            logger.exception("content sync failed for %s", row["path"])
        if i + 1 < total:
            # Cooperative yield between files — do not hog the CPU (#58 / #003).
            time.sleep(0)
        if total and (i + 1 == total or (i + 1) % 25 == 0):
            logger.info("content sync root %s: %s/%s", root_id, i + 1, total)


# Backward-compatible alias.
sync_pdfs_for_root = sync_content_for_root

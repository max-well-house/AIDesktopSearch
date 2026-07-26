"""Persist PDF page text into SQLite FTS (#55 / Decision #006)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from db import connect
from indexer.pdf_extract import extract_pdf

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
    """Remove FTS pages and file_content row for a file id."""
    with connect() as conn:
        conn.execute("DELETE FROM file_pages_fts WHERE file_id = ?", (file_id,))
        conn.execute("DELETE FROM file_content WHERE file_id = ?", (file_id,))
        conn.commit()


def sync_pdf_content(file_id: int, path: Path | str, mtime: float | None) -> None:
    """
    Extract PDF text and replace FTS + file_content for file_id.

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
        extracted = extract_pdf(path_str)
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
                ) VALUES (?, 'pymupdf', NULL, NULL, ?, 'error', ?, ?)
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


def maybe_sync_path(path: Path | str) -> None:
    """
    Sync or clear content for a path already present in ``files``.

    PDFs → sync_pdf_content; non-PDFs with leftover content → clear.
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

    if extension == "pdf":
        sync_pdf_content(file_id, path_str, mtime)
    elif has_content:
        clear_file_content(file_id)


def sync_pdfs_for_root(root_id: int) -> None:
    """
    After a bulk replace_root_files, sync every PDF under the root.

    Single-threaded and lean (#58): one PDF at a time, cooperative yield
    between files so the OS can schedule other work (search / future Ollama).
    """
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, path, mtime FROM files
            WHERE root_id = ? AND extension = 'pdf'
            """,
            (root_id,),
        ).fetchall()
    total = len(rows)
    for i, row in enumerate(rows):
        try:
            mtime = float(row["mtime"]) if row["mtime"] is not None else None
            sync_pdf_content(int(row["id"]), row["path"], mtime)
        except Exception:  # noqa: BLE001
            logger.exception("PDF sync failed for %s", row["path"])
        if i + 1 < total:
            # Cooperative yield between files — do not hog the CPU (#58 / #003).
            time.sleep(0)
        if total and (i + 1 == total or (i + 1) % 25 == 0):
            logger.info("PDF sync root %s: %s/%s", root_id, i + 1, total)

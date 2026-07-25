"""Classic filename + PDF content search against SQLite (#42 / #56)."""

from __future__ import annotations

import re

from db import connect

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

# FTS5 MATCH metacharacters / operators — strip so user input stays literal-ish.
_FTS_SPECIAL = re.compile(r'["\*\^\(\)\{\}:\-]|OR\b|AND\b|NOT\b|NEAR\b', re.IGNORECASE)


def _escape_like(value: str) -> str:
    """Escape LIKE metacharacters so user input is matched literally."""
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _fts_match_query(query: str) -> str | None:
    """
    Build a safe FTS5 MATCH expression: quoted tokens joined with AND.

    Returns None if nothing searchable remains after sanitizing.
    """
    cleaned = _FTS_SPECIAL.sub(" ", query)
    tokens = [t for t in cleaned.split() if t]
    if not tokens:
        return None
    parts: list[str] = []
    for tok in tokens:
        safe = tok.replace('"', "")
        if not safe:
            continue
        parts.append(f'"{safe}"')
    if not parts:
        return None
    return " AND ".join(parts)


def _hit_from_row(row, *, page: int | None, match: str) -> dict:
    return {
        "id": int(row["id"]),
        "path": row["path"],
        "name": row["name"],
        "extension": row["extension"],
        "size": int(row["size"]) if row["size"] is not None else None,
        "mtime": float(row["mtime"]) if row["mtime"] is not None else None,
        "root_id": int(row["root_id"]) if row["root_id"] is not None else None,
        "page": page,
        "match": match,
    }


def search_filenames(query: str, *, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """
    Case-insensitive substring match on files.name plus PDF body FTS (#56).

    Empty/whitespace query returns []. One hit per file: filename matches rank
    above content-only; content contributes the lowest matching page.
    Cap with limit (clamped 1..MAX_LIMIT).
    """
    q = (query or "").strip()
    if not q:
        return []

    capped = max(1, min(int(limit), MAX_LIMIT))
    pattern = f"%{_escape_like(q)}%"
    prefix = f"{_escape_like(q)}%"
    fts_q = _fts_match_query(q)

    by_id: dict[int, dict] = {}

    with connect() as conn:
        name_rows = conn.execute(
            """
            SELECT id, path, name, extension, size, mtime, root_id,
              CASE
                WHEN name LIKE ? ESCAPE '\\' COLLATE NOCASE THEN 0
                ELSE 1
              END AS name_rank
            FROM files
            WHERE name LIKE ? ESCAPE '\\' COLLATE NOCASE
            ORDER BY name_rank, name COLLATE NOCASE
            LIMIT ?
            """,
            (prefix, pattern, capped),
        ).fetchall()

        for row in name_rows:
            fid = int(row["id"])
            by_id[fid] = _hit_from_row(
                row,
                page=None,
                match="filename",
            )
            by_id[fid]["_rank"] = int(row["name_rank"])  # 0 prefix, 1 substring

        if fts_q:
            try:
                content_rows = conn.execute(
                    """
                    SELECT f.id, f.path, f.name, f.extension, f.size, f.mtime, f.root_id,
                           MIN(fts.page) AS match_page
                    FROM file_pages_fts AS fts
                    JOIN files AS f ON f.id = fts.file_id
                    WHERE file_pages_fts MATCH ?
                    GROUP BY f.id
                    ORDER BY f.name COLLATE NOCASE
                    LIMIT ?
                    """,
                    (fts_q, capped),
                ).fetchall()
            except Exception:  # noqa: BLE001 — bad MATCH should not 500
                content_rows = []

            for row in content_rows:
                fid = int(row["id"])
                page = int(row["match_page"]) if row["match_page"] is not None else None
                if fid in by_id:
                    by_id[fid]["page"] = page
                    by_id[fid]["match"] = "both"
                else:
                    by_id[fid] = _hit_from_row(row, page=page, match="content")
                    by_id[fid]["_rank"] = 2  # after filename hits

    merged = list(by_id.values())
    merged.sort(
        key=lambda h: (
            int(h.get("_rank", 2)),
            (h.get("name") or "").lower(),
        )
    )
    out: list[dict] = []
    for hit in merged[:capped]:
        hit.pop("_rank", None)
        out.append(hit)
    return out

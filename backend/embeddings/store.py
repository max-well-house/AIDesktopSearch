"""Persist chunk embeddings in SQLite + sqlite-vec (#67 / Decision #008)."""

from __future__ import annotations

import json
import logging
import math
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from db import connect
from embeddings.vec import VEC_DIMENSION, ensure_vec_schema, load_sqlite_vec

logger = logging.getLogger(__name__)

DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_EMBED_DIM = VEC_DIMENSION
SMOKE_MODEL_ID = "__smoke__"


@dataclass(frozen=True)
class ChunkRecord:
    """One chunk to persist (metadata + embedding)."""

    chunk_index: int
    embedding: Sequence[float]
    page: int | None = None
    text_preview: str | None = None
    content_hash: str | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def serialize_f32(vector: Sequence[float]) -> bytes:
    """Pack float32 little-endian for sqlite-vec BLOB inserts."""
    return struct.pack(f"<{len(vector)}f", *[float(x) for x in vector])


def vector_store_status() -> dict:
    """Capability snapshot for /health and System Status."""
    with connect() as conn:
        loaded = load_sqlite_vec(conn)
        chunk_count = 0
        if loaded["available"]:
            try:
                ensure_vec_schema(conn)
                conn.commit()
                chunk_count = int(
                    conn.execute("SELECT COUNT(*) AS c FROM embedding_chunks").fetchone()[
                        "c"
                    ]
                )
            except Exception as exc:  # noqa: BLE001 — soft-fail for status
                loaded = {
                    **loaded,
                    "available": False,
                    "note": f"vec schema error: {exc}",
                }
        return {
            "available": bool(loaded["available"]),
            "version": loaded.get("version"),
            "note": loaded.get("note"),
            "dimension": int(loaded.get("dimension") or DEFAULT_EMBED_DIM),
            "chunk_count": chunk_count,
        }


def embedding_chunk_count() -> int:
    with connect() as conn:
        try:
            return int(
                conn.execute("SELECT COUNT(*) AS c FROM embedding_chunks").fetchone()["c"]
            )
        except Exception:  # noqa: BLE001
            return 0


def clear_file_embeddings(file_id: int) -> None:
    """Delete chunk metadata (+ vec rows via trigger) for a file."""
    with connect() as conn:
        # Ensure trigger exists when extension is available.
        ensure_vec_schema(conn)
        conn.execute("DELETE FROM embedding_chunks WHERE file_id = ?", (int(file_id),))
        conn.commit()


def replace_file_embeddings(
    file_id: int,
    chunks: Sequence[ChunkRecord],
    *,
    model_id: str = DEFAULT_EMBED_MODEL,
    dim: int = DEFAULT_EMBED_DIM,
) -> int:
    """
    Replace all embeddings for ``file_id`` + ``model_id``.

    Raises RuntimeError if sqlite-vec is unavailable or dim mismatches the
    locked vec0 schema.
    """
    if dim != DEFAULT_EMBED_DIM:
        raise ValueError(
            f"embedding dim {dim} != locked store dim {DEFAULT_EMBED_DIM}; "
            "recreate vec schema before mixing models"
        )

    with connect() as conn:
        if not ensure_vec_schema(conn):
            raise RuntimeError("sqlite-vec is not available; cannot store embeddings")

        conn.execute(
            "DELETE FROM embedding_chunks WHERE file_id = ? AND model_id = ?",
            (int(file_id), model_id),
        )
        # Defensive: clear any orphan vec rows left after a partial wipe / missed trigger.
        try:
            conn.execute(
                """
                DELETE FROM vec_chunks
                WHERE chunk_id NOT IN (SELECT id FROM embedding_chunks)
                """
            )
        except Exception:
            pass

        inserted = 0
        now = _utc_now()
        for chunk in chunks:
            if len(chunk.embedding) != dim:
                raise ValueError(
                    f"chunk {chunk.chunk_index} has dim {len(chunk.embedding)}, expected {dim}"
                )
            preview = chunk.text_preview
            if preview is not None and len(preview) > 500:
                preview = preview[:500]

            cur = conn.execute(
                """
                INSERT INTO embedding_chunks (
                    file_id, page, chunk_index, text_preview,
                    model_id, dim, content_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(file_id),
                    chunk.page,
                    int(chunk.chunk_index),
                    preview,
                    model_id,
                    dim,
                    chunk.content_hash,
                    now,
                ),
            )
            chunk_id = int(cur.lastrowid)
            blob = serialize_f32(chunk.embedding)
            try:
                conn.execute(
                    "INSERT INTO vec_chunks(chunk_id, embedding) VALUES (?, ?)",
                    (chunk_id, blob),
                )
            except Exception:
                # Last resort if an orphan PK still blocks insert.
                conn.execute(
                    "DELETE FROM vec_chunks WHERE chunk_id = ?", (chunk_id,)
                )
                conn.execute(
                    "INSERT INTO vec_chunks(chunk_id, embedding) VALUES (?, ?)",
                    (chunk_id, blob),
                )
            inserted += 1

        conn.commit()
        return inserted


def knn_chunks(
    query: Sequence[float],
    *,
    k: int = 10,
    model_id: str | None = None,
) -> list[dict]:
    """
    Nearest-neighbor over stored chunk vectors.

    Returns dicts with chunk_id, file_id, page, chunk_index, text_preview,
    model_id, distance. Empty list if store unavailable or no rows.
    """
    if not query:
        return []
    if len(query) != DEFAULT_EMBED_DIM:
        raise ValueError(
            f"query dim {len(query)} != locked store dim {DEFAULT_EMBED_DIM}"
        )

    capped_k = max(1, min(int(k), 100))
    blob = serialize_f32(query)

    with connect() as conn:
        if not ensure_vec_schema(conn):
            return []

        # Prefer joining metadata so we can filter model_id.
        sql = """
            SELECT
                v.chunk_id AS chunk_id,
                v.distance AS distance,
                c.file_id AS file_id,
                c.page AS page,
                c.chunk_index AS chunk_index,
                c.text_preview AS text_preview,
                c.model_id AS model_id
            FROM vec_chunks AS v
            JOIN embedding_chunks AS c ON c.id = v.chunk_id
            WHERE v.embedding MATCH ?
              AND k = ?
        """
        params: list = [blob, capped_k]
        if model_id is not None:
            sql += " AND c.model_id = ?"
            params.append(model_id)

        rows = conn.execute(sql, params).fetchall()
        return [
            {
                "chunk_id": int(row["chunk_id"]),
                "file_id": int(row["file_id"]),
                "page": int(row["page"]) if row["page"] is not None else None,
                "chunk_index": int(row["chunk_index"]),
                "text_preview": row["text_preview"],
                "model_id": row["model_id"],
                "distance": float(row["distance"]),
            }
            for row in rows
        ]


def run_store_smoke() -> dict:
    """
    Round-trip a throwaway vector for System Status verification (#67).

    Requires at least one indexed file. Cleans up smoke rows afterward.
    """
    status = vector_store_status()
    if not status["available"]:
        return {
            "ok": False,
            "error": status.get("note") or "vector store unavailable",
            "version": status.get("version"),
        }

    with connect() as conn:
        row = conn.execute("SELECT id, name FROM files ORDER BY id LIMIT 1").fetchone()
        if row is None:
            return {
                "ok": False,
                "error": "index a folder first — need at least one file row",
                "version": status.get("version"),
            }
        file_id = int(row["id"])
        file_name = row["name"]

    # Unit vector with a distinctive pattern.
    vec = [0.0] * DEFAULT_EMBED_DIM
    vec[0] = 1.0
    # Normalize for cosine friendliness (already unit length).
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    vec = [x / norm for x in vec]

    try:
        replace_file_embeddings(
            file_id,
            [
                ChunkRecord(
                    chunk_index=0,
                    embedding=vec,
                    page=1,
                    text_preview="__smoke__ vector store check",
                    content_hash="smoke",
                )
            ],
            model_id=SMOKE_MODEL_ID,
            dim=DEFAULT_EMBED_DIM,
        )
        hits = knn_chunks(vec, k=1, model_id=SMOKE_MODEL_ID)
    finally:
        with connect() as conn:
            ensure_vec_schema(conn)
            conn.execute(
                "DELETE FROM embedding_chunks WHERE file_id = ? AND model_id = ?",
                (file_id, SMOKE_MODEL_ID),
            )
            conn.commit()

    if not hits:
        return {
            "ok": False,
            "error": "smoke insert succeeded but k-NN returned no hits",
            "version": status.get("version"),
            "file_id": file_id,
            "file_name": file_name,
        }

    distance = float(hits[0]["distance"])
    return {
        "ok": True,
        "version": status.get("version"),
        "file_id": file_id,
        "file_name": file_name,
        "distance": distance,
        "detail": json.dumps(
            {"chunk_id": hits[0]["chunk_id"], "distance": distance},
            separators=(",", ":"),
        ),
    }

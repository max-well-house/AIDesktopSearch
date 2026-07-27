"""Generate embeddings for indexed file text (#66)."""

from __future__ import annotations

import hashlib
import logging

from db import connect
from embeddings.chunk import chunk_pages
from embeddings.client import EmbedClientError, embed_texts, model_available
from embeddings.store import (
    DEFAULT_EMBED_DIM,
    DEFAULT_EMBED_MODEL,
    ChunkRecord,
    clear_file_embeddings,
    replace_file_embeddings,
    vector_store_status,
)

logger = logging.getLogger(__name__)

# Small batches keep Ollama memory predictable on the primary profile.
EMBED_BATCH_SIZE = 8


def _page_rows(file_id: int) -> list[tuple[int, str]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT page, text
            FROM file_pages_fts
            WHERE file_id = ?
            ORDER BY page
            """,
            (int(file_id),),
        ).fetchall()
    return [(int(r["page"]), str(r["text"] or "")) for r in rows]


def list_pending_embed_file_ids(
    *,
    model_id: str = DEFAULT_EMBED_MODEL,
) -> list[int]:
    """
    File ids that have FTS text but no chunks for ``model_id``.

    Used for backfill after #67 / first install of an embed model.
    """
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT fts.file_id AS file_id
            FROM file_pages_fts AS fts
            WHERE NOT EXISTS (
                SELECT 1 FROM embedding_chunks AS c
                WHERE c.file_id = fts.file_id AND c.model_id = ?
            )
            ORDER BY fts.file_id
            """,
            (model_id,),
        ).fetchall()
    return [int(r["file_id"]) for r in rows]


def embed_file(
    file_id: int,
    *,
    model_id: str = DEFAULT_EMBED_MODEL,
    dim: int = DEFAULT_EMBED_DIM,
) -> dict:
    """
    Chunk FTS text for ``file_id``, embed via Ollama, persist via store.

    Returns a summary dict. Soft-skips when there is no text. Raises on hard
    store/client failures so the queue can record last_error.
    """
    fid = int(file_id)
    vs = vector_store_status()
    if not vs.get("available"):
        raise RuntimeError(vs.get("note") or "vector store unavailable")

    if not model_available(model_id):
        raise EmbedClientError(
            f"embed model {model_id!r} not available — run: ollama pull {model_id}"
        )

    pages = _page_rows(fid)
    if not pages:
        clear_file_embeddings(fid)
        return {
            "file_id": fid,
            "status": "empty",
            "chunks": 0,
            "model_id": model_id,
        }

    text_chunks = chunk_pages(pages)
    if not text_chunks:
        clear_file_embeddings(fid)
        return {
            "file_id": fid,
            "status": "empty",
            "chunks": 0,
            "model_id": model_id,
        }

    records: list[ChunkRecord] = []
    batch_texts: list[str] = []
    batch_meta: list[tuple[int, int | None, str]] = []

    def flush() -> None:
        nonlocal batch_texts, batch_meta
        if not batch_texts:
            return
        vectors = embed_texts(batch_texts, model=model_id, expected_dim=dim)
        for (chunk_index, page, preview), vec, text in zip(
            batch_meta, vectors, batch_texts, strict=True
        ):
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            records.append(
                ChunkRecord(
                    chunk_index=chunk_index,
                    embedding=vec,
                    page=page,
                    text_preview=preview,
                    content_hash=digest,
                )
            )
        batch_texts = []
        batch_meta = []

    for ch in text_chunks:
        preview = ch.text if len(ch.text) <= 500 else ch.text[:500]
        batch_texts.append(ch.text)
        batch_meta.append((ch.chunk_index, ch.page, preview))
        if len(batch_texts) >= EMBED_BATCH_SIZE:
            flush()
    flush()

    written = replace_file_embeddings(
        fid, records, model_id=model_id, dim=dim
    )
    return {
        "file_id": fid,
        "status": "ok",
        "chunks": written,
        "model_id": model_id,
    }

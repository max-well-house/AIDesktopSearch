"""Hybrid query routing — classic first (#98 / Decision #002 / #68).

Semantic path: embed query → k-NN over stored chunks. Full merge/rank is #69.
LLM/RAG remains a stub (v0.8).
"""

from __future__ import annotations

import logging
from typing import Literal

from indexer.search import DEFAULT_LIMIT, MAX_LIMIT, search_filenames

logger = logging.getLogger(__name__)

SearchMode = Literal["classic", "semantic", "llm", "auto"]

STAGES_LATER: tuple[str, ...] = ("semantic", "llm")


def classify_query(query: str) -> Literal["classic"]:
    """
    Pick the primary search stage for this query.

    Stub: always classic. Escalation heuristics stay in #69.
    """
    _ = (query or "").strip()
    return "classic"


def run_classic(query: str, *, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Filename + content keyword path (#42 / #56)."""
    return search_filenames(query, limit=limit)


def run_semantic(query: str, *, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """
    Meaning search: embed the query, k-NN over sqlite-vec, map to files (#68).

    Soft-fails to [] when the store is empty/unavailable or Ollama cannot
    embed the query (Decision #003 / #008). Does not call the chat LLM.
    """
    q = (query or "").strip()
    if not q:
        return []

    capped = max(1, min(int(limit), MAX_LIMIT))

    try:
        from db import connect
        from embeddings.client import EmbedClientError, embed_texts
        from embeddings.store import (
            DEFAULT_EMBED_MODEL,
            knn_chunks,
            vector_store_status,
        )
    except Exception:  # noqa: BLE001
        logger.debug("semantic imports failed", exc_info=True)
        return []

    status = vector_store_status()
    if not status.get("available") or int(status.get("chunk_count") or 0) <= 0:
        return []

    try:
        vectors = embed_texts([q], model=DEFAULT_EMBED_MODEL)
    except EmbedClientError as exc:
        logger.info("semantic query embed unavailable: %s", exc)
        return []
    except Exception:  # noqa: BLE001
        logger.exception("semantic query embed failed")
        return []

    if not vectors:
        return []

    # Over-fetch chunks so file-level dedupe can still fill ``limit``.
    knn_k = min(max(capped * 4, 16), 80)
    try:
        chunk_hits = knn_chunks(
            vectors[0],
            k=knn_k,
            model_id=DEFAULT_EMBED_MODEL,
        )
    except Exception:  # noqa: BLE001
        logger.exception("semantic k-NN failed")
        return []

    if not chunk_hits:
        return []

    best_by_file: dict[int, dict] = {}
    for hit in chunk_hits:
        fid = int(hit["file_id"])
        prev = best_by_file.get(fid)
        if prev is None or float(hit["distance"]) < float(prev["distance"]):
            best_by_file[fid] = hit

    ordered = sorted(
        best_by_file.values(),
        key=lambda h: (float(h["distance"]), int(h["file_id"])),
    )[:capped]
    file_ids = [int(h["file_id"]) for h in ordered]
    if not file_ids:
        return []

    placeholders = ",".join("?" * len(file_ids))
    with connect() as conn:
        rows = {
            int(row["id"]): row
            for row in conn.execute(
                f"""
                SELECT id, path, name, extension, size, mtime, root_id
                FROM files
                WHERE id IN ({placeholders})
                """,
                file_ids,
            )
        }

    results: list[dict] = []
    for hit in ordered:
        row = rows.get(int(hit["file_id"]))
        if row is None:
            continue
        page = hit.get("page")
        results.append(
            {
                "id": int(row["id"]),
                "path": row["path"],
                "name": row["name"],
                "extension": row["extension"],
                "size": int(row["size"]) if row["size"] is not None else None,
                "mtime": float(row["mtime"]) if row["mtime"] is not None else None,
                "root_id": int(row["root_id"]) if row["root_id"] is not None else None,
                "page": int(page) if page is not None else None,
                "match": "semantic",
            }
        )
    return results


def run_llm(query: str, *, limit: int = DEFAULT_LIMIT) -> None:
    """Placeholder for RAG answers + citations (v0.8). Not called yet."""
    _ = (query, limit)
    return None


def _vectors_ready() -> bool:
    try:
        from embeddings.store import vector_store_status

        status = vector_store_status()
        return bool(status.get("available")) and int(status.get("chunk_count") or 0) > 0
    except Exception:  # noqa: BLE001
        return False


def execute_search(
    query: str,
    *,
    limit: int = DEFAULT_LIMIT,
    mode: Literal["classic", "semantic", "auto"] = "classic",
) -> dict:
    """
    Route and run search.

    - classic (default): filename/FTS only; semantic/LLM skipped.
    - semantic: meaning search only (#68).
    - auto: classic first; if zero hits and vectors exist, one semantic retry (#68 test wire).
    """
    q = (query or "").strip()
    capped = max(1, min(int(limit), MAX_LIMIT))
    requested = (mode or "classic").strip().lower()
    if requested not in ("classic", "semantic", "auto"):
        requested = "classic"

    if requested == "semantic":
        results = run_semantic(q, limit=capped)
        return {
            "query": q,
            "count": len(results),
            "results": results,
            "mode": "semantic",
            "stages_skipped": ["classic", "llm"],
        }

    # classic or auto — always try classic first (Decision #002).
    results = run_classic(q, limit=capped)
    if requested == "classic":
        return {
            "query": q,
            "count": len(results),
            "results": results,
            "mode": "classic",
            "stages_skipped": list(STAGES_LATER),
        }

    # auto: empty-classic salvage via semantic when vectors are ready.
    if results or not q or not _vectors_ready():
        return {
            "query": q,
            "count": len(results),
            "results": results,
            "mode": "classic",
            "stages_skipped": list(STAGES_LATER),
        }

    semantic_hits = run_semantic(q, limit=capped)
    if semantic_hits:
        return {
            "query": q,
            "count": len(semantic_hits),
            "results": semantic_hits,
            "mode": "semantic",
            "stages_skipped": ["llm"],
        }

    return {
        "query": q,
        "count": 0,
        "results": [],
        "mode": "classic",
        "stages_skipped": list(STAGES_LATER),
    }

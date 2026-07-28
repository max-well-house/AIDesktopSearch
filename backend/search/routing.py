"""Hybrid query routing — classic first (#98 / Decision #002 / #68 / #69).

Order: classic → semantic when needed → LLM later (v0.8 stub).
Full hybrid (#69): merge classic + semantic; ``*.ext`` stays classic-only
unless classic is empty (then escalate to semantic). Short concepts and
phrases use hybrid so meaning relatives fill in (audit 2026-07-28).
"""

from __future__ import annotations

import logging
import re
from typing import Literal

from indexer.search import DEFAULT_LIMIT, MAX_LIMIT, search_filenames

logger = logging.getLogger(__name__)

SearchMode = Literal["classic", "semantic", "hybrid", "llm", "auto"]

STAGES_LATER: tuple[str, ...] = ("semantic", "llm")

# Cosine distance ceiling (sqlite-vec); lower = closer. Nearest file is always kept.
SEMANTIC_MAX_DISTANCE = 0.52

_QUESTION_WORDS = frozenset(
    {
        "what",
        "how",
        "why",
        "when",
        "where",
        "who",
        "which",
        "whom",
        "whose",
        "summarize",
        "explain",
        "describe",
        "compare",
        "find",
        "show",
        "list",
        "tell",
        "bring",
        "related",
        "about",
    }
)

_EXT_SUFFIX = re.compile(r"\.[a-z0-9]{1,8}$", re.IGNORECASE)


def is_filename_like(query: str) -> bool:
    """
    True when classic should own the query alone (Decision #002 example: invoice.pdf).

    Only clear filename / extension lookups skip embedding. Short concepts
    (e.g. ``pokemon``, ``fire dragon``) are hybrid so meaning search can run.
    """
    q = (query or "").strip()
    if not q:
        return True
    lower = q.lower()
    tokens = q.split()
    first = tokens[0].lower().rstrip("?.,!;:") if tokens else ""
    if lower.endswith("?"):
        return False
    if first in _QUESTION_WORDS:
        return False
    if _EXT_SUFFIX.search(tokens[-1] if tokens else ""):
        return True
    return False


def classify_query(query: str) -> Literal["classic", "hybrid"]:
    """
    Pick classic-only vs hybrid (classic + semantic merge).

    LLM never selected here (v0.8).
    """
    q = (query or "").strip()
    if not q or is_filename_like(q):
        return "classic"
    return "hybrid"


def run_classic(query: str, *, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Filename + content keyword path (#42 / #56)."""
    return search_filenames(query, limit=limit)


def _filter_by_distance(ordered: list[dict]) -> list[dict]:
    """Drop weak neighbors; always keep the nearest file when anything matched."""
    if not ordered:
        return []
    kept = [
        hit
        for hit in ordered
        if float(hit["distance"]) <= SEMANTIC_MAX_DISTANCE
    ]
    if not kept:
        return ordered[:1]
    return kept


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
    )
    ordered = _filter_by_distance(ordered)[:capped]
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
                "distance": float(hit["distance"]),
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


def merge_hybrid_results(
    classic: list[dict],
    semantic: list[dict],
    *,
    limit: int,
) -> list[dict]:
    """
    Merge classic + semantic hits (#69).

    Classic order wins for overlapping files; semantic fills gaps and may
    supply a page when classic had none. Match becomes ``hybrid`` when both
    paths contributed the same file.
    """
    capped = max(1, min(int(limit), MAX_LIMIT))
    by_id: dict[int, dict] = {}
    order: list[int] = []

    for hit in classic:
        fid = int(hit["id"])
        if fid in by_id:
            continue
        by_id[fid] = dict(hit)
        order.append(fid)

    for hit in semantic:
        fid = int(hit["id"])
        if fid in by_id:
            existing = by_id[fid]
            if existing.get("page") is None and hit.get("page") is not None:
                existing["page"] = hit["page"]
            if existing.get("match") != "semantic":
                existing["match"] = "hybrid"
            continue
        by_id[fid] = dict(hit)
        order.append(fid)

    out: list[dict] = []
    for fid in order:
        row = by_id[fid]
        row.pop("_rank", None)
        out.append(row)
        if len(out) >= capped:
            break
    return out


def _pack_semantic_or_hybrid(
    q: str,
    classic_hits: list[dict],
    semantic_hits: list[dict],
    *,
    capped: int,
) -> dict:
    if not semantic_hits:
        return {
            "query": q,
            "count": len(classic_hits),
            "results": classic_hits,
            "mode": "classic",
            "stages_skipped": list(STAGES_LATER),
        }
    if not classic_hits:
        return {
            "query": q,
            "count": len(semantic_hits),
            "results": semantic_hits,
            "mode": "semantic",
            "stages_skipped": ["llm"],
        }
    merged = merge_hybrid_results(classic_hits, semantic_hits, limit=capped)
    return {
        "query": q,
        "count": len(merged),
        "results": merged,
        "mode": "hybrid",
        "stages_skipped": ["llm"],
    }


def execute_search(
    query: str,
    *,
    limit: int = DEFAULT_LIMIT,
    mode: Literal["classic", "semantic", "auto", "hybrid"] = "classic",
) -> dict:
    """
    Route and run search (Decision #002 / #69).

    - classic: filename/FTS only.
    - semantic: meaning search only.
    - auto / hybrid: ``*.ext`` → classic when hits exist; empty classic escalates
      to semantic; other queries merge classic + semantic when vectors exist.
      Soft-fails to classic-only if semantic empty (Ollama down). Never calls LLM.
    """
    q = (query or "").strip()
    capped = max(1, min(int(limit), MAX_LIMIT))
    requested = (mode or "classic").strip().lower()
    if requested not in ("classic", "semantic", "auto", "hybrid"):
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

    if requested == "classic":
        results = run_classic(q, limit=capped)
        return {
            "query": q,
            "count": len(results),
            "results": results,
            "mode": "classic",
            "stages_skipped": list(STAGES_LATER),
        }

    # auto / hybrid
    intent = classify_query(q)
    classic_hits = run_classic(q, limit=capped)
    vectors_ok = bool(q) and _vectors_ready()

    if not vectors_ok:
        return {
            "query": q,
            "count": len(classic_hits),
            "results": classic_hits,
            "mode": "classic",
            "stages_skipped": list(STAGES_LATER),
        }

    # Filename-like with classic hits: stay classic-only (save an embed).
    # Empty classic: escalate to semantic (e.g. missing invoice.pdf → meaning).
    if intent == "classic" and classic_hits:
        return {
            "query": q,
            "count": len(classic_hits),
            "results": classic_hits,
            "mode": "classic",
            "stages_skipped": list(STAGES_LATER),
        }

    semantic_hits = run_semantic(q, limit=capped)
    return _pack_semantic_or_hybrid(q, classic_hits, semantic_hits, capped=capped)

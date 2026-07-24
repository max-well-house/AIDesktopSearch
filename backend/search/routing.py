"""Hybrid query routing stub — classic first (#98 / Decision #002).

v0.3: every query resolves to classic filename search. Semantic and LLM
hooks exist so later milestones (#69 hybrid, v0.8 RAG) can plug in without
reshaping GET /search. Do not call embeddings or Ollama from this module yet.
"""

from __future__ import annotations

from typing import Literal

from indexer.search import DEFAULT_LIMIT, MAX_LIMIT, search_filenames

SearchMode = Literal["classic", "semantic", "llm"]

STAGES_LATER: tuple[SearchMode, ...] = ("semantic", "llm")


def classify_query(query: str) -> SearchMode:
    """
    Pick the primary search stage for this query.

    Stub: always classic. Future heuristics may escalate (question words,
    "summarize", multi-sentence intents) — full hybrid ranking stays in #69.
    """
    _ = (query or "").strip()
    return "classic"


def run_classic(query: str, *, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Filename / keyword path — live for v0.3."""
    return search_filenames(query, limit=limit)


def run_semantic(query: str, *, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Placeholder for embedding search (#69). Not called by execute_search yet."""
    _ = (query, limit)
    return []


def run_llm(query: str, *, limit: int = DEFAULT_LIMIT) -> None:
    """Placeholder for RAG answers + citations (v0.8). Not called yet."""
    _ = (query, limit)
    return None


def execute_search(query: str, *, limit: int = DEFAULT_LIMIT) -> dict:
    """
    Route and run search. Stub always runs classic; semantic/LLM are skipped.

    Returns hits plus observable routing metadata for API/tests.
    """
    q = (query or "").strip()
    capped = max(1, min(int(limit), MAX_LIMIT))
    mode = classify_query(q)
    # Hot path: classic only. Do not invoke run_semantic / run_llm here.
    results = run_classic(q, limit=capped)
    return {
        "query": q,
        "count": len(results),
        "results": results,
        "mode": mode,
        "stages_skipped": list(STAGES_LATER),
    }

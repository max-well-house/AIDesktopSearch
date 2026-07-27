"""Ollama embedding client (#66). Uses POST /api/embed (not legacy /api/embeddings)."""

from __future__ import annotations

import logging
from typing import Sequence

import httpx

from embeddings.store import DEFAULT_EMBED_DIM, DEFAULT_EMBED_MODEL

logger = logging.getLogger(__name__)

# Mirror capabilities.ollama — avoid importing capabilities package here (cycle).
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
EMBED_TIMEOUT_SECONDS = 120.0
TAGS_TIMEOUT_SECONDS = 3.0


class EmbedClientError(RuntimeError):
    """Ollama embed call failed or returned unusable vectors."""


def list_ollama_models(base_url: str = OLLAMA_BASE_URL) -> list[str]:
    """Return model names from GET /api/tags (empty on failure)."""
    try:
        with httpx.Client(timeout=TAGS_TIMEOUT_SECONDS) as client:
            response = client.get(f"{base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.debug("ollama /api/tags failed: %s", exc)
        return []

    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return []
    names: list[str] = []
    for item in models:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("model")
        if name:
            names.append(str(name))
    return names


def model_available(
    model: str = DEFAULT_EMBED_MODEL,
    *,
    base_url: str = OLLAMA_BASE_URL,
) -> bool:
    """True if tags list a matching model (exact or ``name:tag`` prefix)."""
    want = model.strip().lower()
    if not want:
        return False
    for name in list_ollama_models(base_url=base_url):
        n = name.lower()
        if n == want or n.startswith(want + ":"):
            return True
    return False


def embed_texts(
    texts: Sequence[str],
    *,
    model: str = DEFAULT_EMBED_MODEL,
    base_url: str = OLLAMA_BASE_URL,
    expected_dim: int = DEFAULT_EMBED_DIM,
) -> list[list[float]]:
    """
    Embed one or more strings via Ollama ``/api/embed``.

    Returns one vector per non-empty input string, in order. Raises
    EmbedClientError on transport/API/shape failures.
    """
    cleaned = [(t or "").strip() for t in texts]
    if not cleaned or any(not t for t in cleaned):
        raise EmbedClientError("embed_texts requires non-empty strings")

    url = f"{base_url.rstrip('/')}/api/embed"
    payload = {"model": model, "input": cleaned if len(cleaned) > 1 else cleaned[0]}
    try:
        with httpx.Client(timeout=EMBED_TIMEOUT_SECONDS) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        raise EmbedClientError(f"Ollama embed request failed: {exc}") from exc
    except ValueError as exc:
        raise EmbedClientError(f"Ollama embed returned non-JSON: {exc}") from exc

    vectors = body.get("embeddings") if isinstance(body, dict) else None
    if not isinstance(vectors, list) or len(vectors) != len(cleaned):
        raise EmbedClientError(
            f"expected {len(cleaned)} embedding(s), got "
            f"{len(vectors) if isinstance(vectors, list) else type(vectors)}"
        )

    out: list[list[float]] = []
    for i, vec in enumerate(vectors):
        if not isinstance(vec, (list, tuple)) or not vec:
            raise EmbedClientError(f"embedding[{i}] missing or empty")
        floats = [float(x) for x in vec]
        if len(floats) != expected_dim:
            raise EmbedClientError(
                f"embedding[{i}] dim {len(floats)} != expected {expected_dim}"
            )
        out.append(floats)
    return out

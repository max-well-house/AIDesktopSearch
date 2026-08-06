"""Ollama chat client (#70). Uses POST /api/chat; soft-fails via ChatClientError."""

from __future__ import annotations

import logging
from typing import Sequence

import httpx

from embeddings.client import OLLAMA_BASE_URL, model_available

logger = logging.getLogger(__name__)

# Small default that fits Decision #003 primary profile (16GB RAM + 8GB VRAM).
DEFAULT_CHAT_MODEL = "llama3.2:3b"
CHAT_TIMEOUT_SECONDS = 120.0


class ChatClientError(RuntimeError):
    """Ollama chat call failed or returned an unusable reply."""


def chat_model_available(
    model: str = DEFAULT_CHAT_MODEL,
    *,
    base_url: str = OLLAMA_BASE_URL,
) -> bool:
    """True when tags list includes the chat model (exact or name:tag prefix)."""
    return model_available(model, base_url=base_url)


def chat(
    prompt: str,
    *,
    model: str = DEFAULT_CHAT_MODEL,
    system: str | None = None,
    base_url: str = OLLAMA_BASE_URL,
    timeout: float = CHAT_TIMEOUT_SECONDS,
) -> str:
    """
    Send a single-turn prompt to a local Ollama chat model.

    Ollama prefers GPU when available on the host; we do not pin a vendor.
    Raises ChatClientError on transport/API/empty-reply failures.
    """
    text = (prompt or "").strip()
    if not text:
        raise ChatClientError("chat requires a non-empty prompt")

    messages: list[dict[str, str]] = []
    if system and system.strip():
        messages.append({"role": "system", "content": system.strip()})
    messages.append({"role": "user", "content": text})

    url = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        raise ChatClientError(f"Ollama chat request failed: {exc}") from exc
    except ValueError as exc:
        raise ChatClientError(f"Ollama chat returned non-JSON: {exc}") from exc

    message = body.get("message") if isinstance(body, dict) else None
    if not isinstance(message, dict):
        raise ChatClientError("Ollama chat response missing message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ChatClientError("Ollama chat returned an empty reply")
    return content.strip()


def chat_messages(
    messages: Sequence[dict[str, str]],
    *,
    model: str = DEFAULT_CHAT_MODEL,
    base_url: str = OLLAMA_BASE_URL,
    timeout: float = CHAT_TIMEOUT_SECONDS,
) -> str:
    """Multi-message chat (for RAG in #71). Same error contract as ``chat``."""
    cleaned = [m for m in messages if isinstance(m, dict) and m.get("content")]
    if not cleaned:
        raise ChatClientError("chat_messages requires at least one message")

    url = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": list(cleaned),
        "stream": False,
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        raise ChatClientError(f"Ollama chat request failed: {exc}") from exc
    except ValueError as exc:
        raise ChatClientError(f"Ollama chat returned non-JSON: {exc}") from exc

    message = body.get("message") if isinstance(body, dict) else None
    if not isinstance(message, dict):
        raise ChatClientError("Ollama chat response missing message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ChatClientError("Ollama chat returned an empty reply")
    return content.strip()

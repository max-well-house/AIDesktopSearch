"""Local LLM (Ollama chat) — #70."""

from llm.client import (
    DEFAULT_CHAT_MODEL,
    ChatClientError,
    chat,
    chat_model_available,
)

__all__ = [
    "DEFAULT_CHAT_MODEL",
    "ChatClientError",
    "chat",
    "chat_model_available",
]

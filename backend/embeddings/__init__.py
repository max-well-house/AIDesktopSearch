"""Embedding store + generate (#66–#68)."""

from embeddings.store import (
    DEFAULT_EMBED_DIM,
    DEFAULT_EMBED_MODEL,
    ChunkRecord,
    clear_file_embeddings,
    embedding_chunk_count,
    knn_chunks,
    replace_file_embeddings,
    run_store_smoke,
    vector_store_status,
)
from embeddings.queue import EmbedQueue, get_embed_queue
from embeddings.generate import embed_file, list_pending_embed_file_ids
from embeddings.client import model_available

__all__ = [
    "DEFAULT_EMBED_DIM",
    "DEFAULT_EMBED_MODEL",
    "ChunkRecord",
    "EmbedQueue",
    "clear_file_embeddings",
    "embed_file",
    "embedding_chunk_count",
    "get_embed_queue",
    "knn_chunks",
    "list_pending_embed_file_ids",
    "model_available",
    "replace_file_embeddings",
    "run_store_smoke",
    "vector_store_status",
]

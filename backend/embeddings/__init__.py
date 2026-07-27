"""Embedding store + (later) generate/search (#66–#68)."""

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

__all__ = [
    "DEFAULT_EMBED_DIM",
    "DEFAULT_EMBED_MODEL",
    "ChunkRecord",
    "clear_file_embeddings",
    "embedding_chunk_count",
    "knn_chunks",
    "replace_file_embeddings",
    "run_store_smoke",
    "vector_store_status",
]

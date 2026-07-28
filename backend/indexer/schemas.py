"""Pydantic models for index status / scan / roots / search (#40–#42, #98)."""

from pydantic import BaseModel, Field


class RootStatus(BaseModel):
    id: int
    path: str
    last_scan_at: str | None = None
    file_count: int = 0


class EmbeddedFileSample(BaseModel):
    """One file that already has stored chunks (#66 verify)."""

    file_id: int
    name: str
    chunks: int


class IndexStatusResponse(BaseModel):
    file_count: int
    root_count: int
    last_indexed_at: str | None = None
    roots: list[RootStatus] = Field(default_factory=list)
    # Live watching (#48–#52)
    watching: bool = False
    watched_roots: int = 0
    queue_depth: int = 0
    watch_paused: bool = False
    # Embedding store (#67)
    embedding_chunk_count: int = 0
    vector_store_available: bool = False
    # True when chunks exist and nomic-embed-text is reachable for query embed.
    semantic_query_ready: bool = False
    # Embedding generate (#66)
    embed_queue_depth: int = 0
    embed_paused: bool = False
    embed_completed: int = 0
    embed_failed: int = 0
    embed_last_error: str | None = None
    embed_pending_files: int = 0
    embedded_files: list[EmbeddedFileSample] = Field(default_factory=list)


class WatchControlResponse(BaseModel):
    watching: bool
    watched_roots: int
    queue_depth: int
    paused: bool


class EmbeddingControlResponse(BaseModel):
    """Embed queue pause/resume / status (#66)."""

    running: bool
    paused: bool
    queue_depth: int
    completed: int
    failed: int
    last_error: str | None = None
    last_ok_file_id: int | None = None
    pending_files: int = 0
    model_id: str = "nomic-embed-text"


class EmbeddingBackfillResponse(BaseModel):
    enqueued: int
    pending_files: int
    queue_depth: int
    model_id: str = "nomic-embed-text"


class EmbeddingSmokeResponse(BaseModel):
    """Result of POST /index/embeddings/smoke (#67)."""

    ok: bool
    version: str | None = None
    error: str | None = None
    file_id: int | None = None
    file_name: str | None = None
    distance: float | None = None
    detail: str | None = None


class ScanRequest(BaseModel):
    path: str


class ScanResponse(BaseModel):
    root_id: int
    root_path: str
    files_upserted: int
    files_removed: int
    file_count: int
    root_count: int
    last_indexed_at: str | None = None


class DeleteRootResponse(BaseModel):
    root_id: int
    root_path: str
    files_removed: int
    file_count: int
    root_count: int
    last_indexed_at: str | None = None


class SearchHit(BaseModel):
    id: int
    path: str
    name: str
    extension: str | None = None
    size: int | None = None
    mtime: float | None = None
    root_id: int | None = None
    page: int | None = None
    match: str = "filename"
    distance: float | None = None


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[SearchHit] = Field(default_factory=list)
    mode: str = "classic"
    stages_skipped: list[str] = Field(default_factory=lambda: ["semantic", "llm"])

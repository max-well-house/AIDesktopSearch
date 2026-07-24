"""Pydantic models for index status / scan / roots / search (#40–#42, #98)."""

from pydantic import BaseModel, Field


class RootStatus(BaseModel):
    id: int
    path: str
    last_scan_at: str | None = None
    file_count: int = 0


class IndexStatusResponse(BaseModel):
    file_count: int
    root_count: int
    last_indexed_at: str | None = None
    roots: list[RootStatus] = Field(default_factory=list)


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


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[SearchHit] = Field(default_factory=list)
    mode: str = "classic"
    stages_skipped: list[str] = Field(default_factory=lambda: ["semantic", "llm"])

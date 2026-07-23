"""Pydantic models for index status / scan (#41)."""

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

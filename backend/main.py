from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from capabilities import build_capabilities
from capabilities.schema import HealthResponse
from db import init_db
from indexer import delete_root, index_status, scan_and_save, search_filenames
from indexer.schemas import (
    DeleteRootResponse,
    IndexStatusResponse,
    ScanRequest,
    ScanResponse,
    SearchHit,
    SearchResponse,
)
from indexer.search import DEFAULT_LIMIT, MAX_LIMIT

APP_VERSION = "0.0.3"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Create data/index.db + schema foundation on every process start (#39).
    init_db()
    yield


app = FastAPI(title="AI Desktop Search API", version=APP_VERSION, lifespan=lifespan)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def _health_payload() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        timestamp=_utc_timestamp(),
        capabilities=await build_capabilities(),
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    payload = await _health_payload()
    return JSONResponse(
        content=payload.model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/")
async def root():
    """Compatibility shim — same healthy capability payload as /health."""
    payload = await _health_payload()
    return JSONResponse(
        content=payload.model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/index/status", response_model=IndexStatusResponse)
async def get_index_status():
    """How many files/roots are in SQLite — for Footer + System Status (#41)."""
    return IndexStatusResponse(**index_status())


@app.post("/index/scan", response_model=ScanResponse)
async def post_index_scan(body: ScanRequest):
    """
    Walk a user-selected folder and persist file metadata (#40 / #41).

    Only the given path is scanned — never a silent whole-disk crawl.
    """
    try:
        result = scan_and_save(body.path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ScanResponse(**result)


@app.delete("/index/roots/{root_id}", response_model=DeleteRootResponse)
async def delete_index_root(root_id: int):
    """Remove an indexed folder root and its file rows (#40)."""
    result = delete_root(root_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Root {root_id} not found")
    return DeleteRootResponse(**result)


@app.get("/search", response_model=SearchResponse)
async def get_search(
    q: str = Query("", description="Filename substring (case-insensitive)"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    """Classic filename search — no Ollama required (#42)."""
    hits = search_filenames(q, limit=limit)
    return SearchResponse(
        query=q.strip(),
        count=len(hits),
        results=[SearchHit(**hit) for hit in hits],
    )

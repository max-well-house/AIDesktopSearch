import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from capabilities import build_capabilities
from capabilities.schema import HealthResponse
from db import init_db
from indexer import delete_root, index_status, scan_and_save
from indexer.schemas import (
    DeleteRootResponse,
    EmbeddingSmokeResponse,
    IndexStatusResponse,
    ScanRequest,
    ScanResponse,
    SearchHit,
    SearchResponse,
    WatchControlResponse,
)
from indexer.search import DEFAULT_LIMIT, MAX_LIMIT
from indexer.watch import get_watch_manager
from search import execute_search
from embeddings.store import run_store_smoke

APP_VERSION = "0.0.4"


def _reconcile_and_watch_all() -> None:
    """Startup: rescan each root (catch offline changes), then start watchers."""
    status = index_status()
    manager = get_watch_manager()
    manager.start()
    for root in status.get("roots") or []:
        path = root.get("path")
        root_id = root.get("id")
        if not path or root_id is None:
            continue
        try:
            scan_and_save(path)
        except (FileNotFoundError, NotADirectoryError, OSError):
            # Root missing (e.g. unplugged drive) — skip watch until rescan.
            continue
        manager.watch_root(int(root_id), path)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Create data/index.db + schema foundation on every process start (#39).
    init_db()
    _reconcile_and_watch_all()
    try:
        yield
    finally:
        get_watch_manager().stop()


app = FastAPI(title="AI Desktop Search API", version=APP_VERSION, lifespan=lifespan)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _status_with_watch() -> dict:
    payload = index_status()
    watch = get_watch_manager().status()
    payload["watching"] = watch["watching"]
    payload["watched_roots"] = watch["watched_roots"]
    payload["queue_depth"] = watch["queue_depth"]
    payload["watch_paused"] = watch["paused"]
    return payload


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
    return IndexStatusResponse(**_status_with_watch())


@app.post("/index/scan", response_model=ScanResponse)
async def post_index_scan(body: ScanRequest):
    """
    Walk a user-selected folder and persist file metadata (#40 / #41).

    Only the given path is scanned — never a silent whole-disk crawl.
    Starts live watching for the root after a successful scan (#48–#52).
    PDF extract runs in a worker thread so the event loop stays responsive (#58).
    """
    try:
        result = await asyncio.to_thread(scan_and_save, body.path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    get_watch_manager().watch_root(result["root_id"], result["root_path"])
    return ScanResponse(**result)


@app.delete("/index/roots/{root_id}", response_model=DeleteRootResponse)
async def delete_index_root(root_id: int):
    """Remove an indexed folder root and its file rows (#40)."""
    get_watch_manager().unwatch_root(root_id)
    result = delete_root(root_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Root {root_id} not found")
    return DeleteRootResponse(**result)


@app.post("/index/watch/pause", response_model=WatchControlResponse)
async def pause_watch():
    """Pause live index updates without freezing the API (#52 / Decision #003)."""
    manager = get_watch_manager()
    manager.pause()
    return WatchControlResponse(**manager.status())


@app.post("/index/watch/resume", response_model=WatchControlResponse)
async def resume_watch():
    """Resume draining the watcher queue after pause."""
    manager = get_watch_manager()
    manager.resume()
    return WatchControlResponse(**manager.status())


@app.post("/index/embeddings/smoke", response_model=EmbeddingSmokeResponse)
async def post_embeddings_smoke():
    """
    Round-trip a throwaway vector to verify sqlite-vec (#67).

    Requires at least one indexed file. Does not leave smoke rows behind.
    """
    result = await asyncio.to_thread(run_store_smoke)
    return EmbeddingSmokeResponse(**result)


@app.get("/search", response_model=SearchResponse)
async def get_search(
    q: str = Query("", description="Filename substring (case-insensitive)"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    """Routed search — classic-first stub; no Ollama (#42 / #98)."""
    payload = execute_search(q, limit=limit)
    return SearchResponse(
        query=payload["query"],
        count=payload["count"],
        results=[SearchHit(**hit) for hit in payload["results"]],
        mode=payload["mode"],
        stages_skipped=payload["stages_skipped"],
    )

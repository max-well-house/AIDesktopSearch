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
    EmbeddingBackfillResponse,
    EmbeddingControlResponse,
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
from embeddings.queue import get_embed_queue
from embeddings.generate import list_pending_embed_file_ids
from embeddings.store import DEFAULT_EMBED_MODEL

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
    get_embed_queue().start()
    _reconcile_and_watch_all()
    try:
        yield
    finally:
        get_watch_manager().stop()
        get_embed_queue().stop()


app = FastAPI(title="AI Desktop Search API", version=APP_VERSION, lifespan=lifespan)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _status_with_watch() -> dict:
    payload = index_status()
    watch = get_watch_manager().status()
    embed = get_embed_queue().status()
    payload["watching"] = watch["watching"]
    payload["watched_roots"] = watch["watched_roots"]
    payload["queue_depth"] = watch["queue_depth"]
    payload["watch_paused"] = watch["paused"]
    payload["embed_queue_depth"] = embed["queue_depth"]
    payload["embed_paused"] = embed["paused"]
    payload["embed_completed"] = embed["completed"]
    payload["embed_failed"] = embed["failed"]
    payload["embed_last_error"] = embed["last_error"]
    try:
        payload["embed_pending_files"] = len(list_pending_embed_file_ids())
    except Exception:
        payload["embed_pending_files"] = 0
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


@app.get("/index/embeddings/status", response_model=EmbeddingControlResponse)
async def get_embeddings_status():
    """Embed queue + pending file count (#66)."""
    q = get_embed_queue().status()
    pending = await asyncio.to_thread(list_pending_embed_file_ids)
    return EmbeddingControlResponse(
        **q,
        pending_files=len(pending),
        model_id=DEFAULT_EMBED_MODEL,
    )


@app.post("/index/embeddings/pause", response_model=EmbeddingControlResponse)
async def pause_embeddings():
    """Pause background embedding generation (Decision #003)."""
    manager = get_embed_queue()
    manager.pause()
    q = manager.status()
    pending = await asyncio.to_thread(list_pending_embed_file_ids)
    return EmbeddingControlResponse(
        **q,
        pending_files=len(pending),
        model_id=DEFAULT_EMBED_MODEL,
    )


@app.post("/index/embeddings/resume", response_model=EmbeddingControlResponse)
async def resume_embeddings():
    """Resume draining the embed queue."""
    manager = get_embed_queue()
    manager.resume()
    q = manager.status()
    pending = await asyncio.to_thread(list_pending_embed_file_ids)
    return EmbeddingControlResponse(
        **q,
        pending_files=len(pending),
        model_id=DEFAULT_EMBED_MODEL,
    )


@app.post("/index/embeddings/backfill", response_model=EmbeddingBackfillResponse)
async def backfill_embeddings():
    """
    Enqueue files that have FTS text but no chunks for the default model (#66).

    Use after installing nomic-embed-text or upgrading from store-only (#67).
    """
    pending = await asyncio.to_thread(list_pending_embed_file_ids)
    manager = get_embed_queue()
    enqueued = manager.enqueue_many(pending)
    return EmbeddingBackfillResponse(
        enqueued=enqueued,
        pending_files=len(pending),
        queue_depth=manager.status()["queue_depth"],
        model_id=DEFAULT_EMBED_MODEL,
    )


@app.get("/search", response_model=SearchResponse)
async def get_search(
    q: str = Query("", description="Search query"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    mode: str = Query(
        "classic",
        description="classic | semantic | auto | hybrid",
    ),
):
    """Routed search — classic / semantic / hybrid (#68 / #69)."""
    allowed = {"classic", "semantic", "auto", "hybrid"}
    resolved = (mode or "classic").strip().lower()
    if resolved not in allowed:
        resolved = "classic"
    payload = execute_search(q, limit=limit, mode=resolved)  # type: ignore[arg-type]
    return SearchResponse(
        query=payload["query"],
        count=payload["count"],
        results=[SearchHit(**hit) for hit in payload["results"]],
        mode=payload["mode"],
        stages_skipped=payload["stages_skipped"],
    )

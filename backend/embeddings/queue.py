"""Pauseable background queue for embedding generation (#66 / Decision #003)."""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)

WORKER_POLL_SECONDS = 0.5


class EmbedQueue:
    """
    Coalesce file_ids and embed them on a daemon worker.

    Pause stops draining (items stay queued). Soft-fail per file: log +
    last_error, continue with the next id.
    """

    def __init__(
        self,
        *,
        embed_fn: Callable[[int], dict] | None = None,
        poll_seconds: float = WORKER_POLL_SECONDS,
    ) -> None:
        self._embed_fn = embed_fn
        self._poll = poll_seconds
        self._lock = threading.RLock()
        self._pending: dict[int, float] = {}  # file_id -> last enqueue monotonic
        self._paused = False
        self._running = False
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None
        self._last_error: str | None = None
        self._last_ok_file_id: int | None = None
        self._completed = 0
        self._failed = 0

    def _resolver(self) -> Callable[[int], dict]:
        if self._embed_fn is not None:
            return self._embed_fn
        from embeddings.generate import embed_file

        return embed_file

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._stop.clear()
            self._worker = threading.Thread(
                target=self._worker_loop,
                name="embed-queue-worker",
                daemon=True,
            )
            self._worker.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._stop.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5.0)
        self._worker = None

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._paused = False

    def enqueue(self, file_id: int) -> None:
        fid = int(file_id)
        with self._lock:
            self._pending[fid] = time.monotonic()

    def enqueue_many(self, file_ids: list[int]) -> int:
        n = 0
        for fid in file_ids:
            self.enqueue(fid)
            n += 1
        return n

    def status(self) -> dict:
        with self._lock:
            return {
                "running": self._running and self._worker is not None,
                "paused": self._paused,
                "queue_depth": len(self._pending),
                "completed": self._completed,
                "failed": self._failed,
                "last_error": self._last_error,
                "last_ok_file_id": self._last_ok_file_id,
            }

    def _pop_next(self) -> int | None:
        with self._lock:
            if self._paused or not self._pending:
                return None
            # Oldest enqueue first.
            fid = min(self._pending.keys(), key=lambda k: self._pending[k])
            del self._pending[fid]
            return fid

    def _worker_loop(self) -> None:
        embed = self._resolver()
        while not self._stop.is_set():
            fid = self._pop_next()
            if fid is None:
                self._stop.wait(self._poll)
                continue
            try:
                result = embed(fid)
                with self._lock:
                    self._completed += 1
                    self._last_ok_file_id = fid
                    if result.get("status") == "ok":
                        self._last_error = None
                logger.info(
                    "embed file_id=%s status=%s chunks=%s",
                    fid,
                    result.get("status"),
                    result.get("chunks"),
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("embed failed for file_id=%s", fid)
                with self._lock:
                    self._failed += 1
                    self._last_error = str(exc)


_manager: EmbedQueue | None = None
_manager_lock = threading.Lock()


def get_embed_queue() -> EmbedQueue:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = EmbedQueue()
        return _manager

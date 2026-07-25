"""Live filesystem watching for opt-in corpus roots (#48–#52, Decision #005).

Pipeline: watchdog event → normalize/filter → enqueue → debounce/coalesce →
batch SQLite worker. Never one index job per raw OS event.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from indexer.ignore import (
    is_hidden_name,
    should_skip_dir,
    should_skip_file,
)
from indexer.metadata import (
    delete_file,
    delete_files_under_prefix,
    rename_file,
    rename_files_under_prefix,
    upsert_file,
)

logger = logging.getLogger(__name__)

DEBOUNCE_SECONDS = 0.75
WORKER_POLL_SECONDS = 0.25

# Cheap editor / lock junk (basename suffix or exact).
_TEMP_SUFFIXES = (".tmp", ".temp", ".swp", ".swx", ".bak", "~")
_TEMP_NAMES = frozenset(
    {
        "thumbs.db",
        "desktop.ini",
        ".ds_store",
    }
)


class EventKind(str, Enum):
    UPSERT = "upsert"  # create or modify (file)
    DELETE = "delete"  # file
    RENAME = "rename"  # file move
    DELETE_TREE = "delete_tree"  # directory gone
    RENAME_TREE = "rename_tree"  # directory moved


@dataclass(frozen=True)
class PendingChange:
    kind: EventKind
    path: str
    dest_path: str | None = None
    is_directory: bool = False


def _norm(path: str | Path) -> Path:
    return Path(path)


def _abs_str(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def path_inside_root(path: Path, root: Path) -> bool:
    """True if path is the root or a descendant after resolve (blocks symlink escape)."""
    try:
        resolved = path.resolve()
        root_resolved = root.resolve()
    except OSError:
        return False
    try:
        resolved.relative_to(root_resolved)
        return True
    except ValueError:
        return False


def is_temp_basename(name: str) -> bool:
    lower = name.lower()
    if lower in _TEMP_NAMES:
        return True
    if name.endswith("~"):
        return True
    return any(lower.endswith(suf) for suf in _TEMP_SUFFIXES)


def should_ignore_path(path: Path, *, root: Path) -> bool:
    """Drop events outside root, under denylisted dirs, hidden, or temp junk."""
    if not path_inside_root(path, root):
        return True

    try:
        rel = path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return True

    parts = rel.parts
    if not parts:
        return False  # the root itself

    # Any intermediate directory that should be skipped → ignore.
    for part in parts[:-1]:
        if should_skip_dir(part):
            return True
        if is_hidden_name(part):
            return True

    basename = parts[-1]
    # For files: skip hidden / temp. For dirs on delete/rename we still process
    # the tree op but skip if the dir itself is denylisted.
    if should_skip_dir(basename):
        return True
    if is_hidden_name(basename):
        return True
    if is_temp_basename(basename):
        return True
    return False


def should_ignore_file_event(path: Path, *, root: Path) -> bool:
    if should_ignore_path(path, root=root):
        return True
    return should_skip_file(path.name)


class _RootHandler(FileSystemEventHandler):
    def __init__(self, manager: WatchManager, root_id: int, root_path: Path) -> None:
        super().__init__()
        self._manager = manager
        self.root_id = root_id
        self.root_path = root_path

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_synthetic:
            return
        self._manager._handle_raw(self.root_id, self.root_path, event)


class WatchManager:
    """Owns observers + debounce queue + batch worker for all corpus roots."""

    def __init__(self, *, debounce_seconds: float = DEBOUNCE_SECONDS) -> None:
        self._debounce = debounce_seconds
        self._lock = threading.RLock()
        self._paused = False
        self._running = False
        # root_id -> (Observer, Path)
        self._observers: dict[int, tuple[Observer, Path]] = {}
        # Coalesce key -> (PendingChange, root_id, last_touch_monotonic)
        self._pending: dict[str, tuple[PendingChange, int, float]] = {}
        self._worker: threading.Thread | None = None
        self._stop = threading.Event()

    # --- public control ---

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._stop.clear()
            self._worker = threading.Thread(
                target=self._worker_loop,
                name="index-watch-worker",
                daemon=True,
            )
            self._worker.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._stop.set()
            root_ids = list(self._observers.keys())
        for rid in root_ids:
            self.unwatch_root(rid)
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5.0)
        self._worker = None

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._paused = False

    @property
    def paused(self) -> bool:
        with self._lock:
            return self._paused

    def status(self) -> dict:
        with self._lock:
            return {
                "watching": len(self._observers) > 0 and self._running and not self._paused,
                "watched_roots": len(self._observers),
                "queue_depth": len(self._pending),
                "paused": self._paused,
            }

    def watch_root(self, root_id: int, root_path: Path | str) -> None:
        """Start recursive watch for an indexed root (idempotent)."""
        path = Path(root_path).resolve()
        if not path.is_dir():
            logger.warning("watch_root: not a directory, skip %s", path)
            return
        with self._lock:
            if not self._running:
                self.start()
            existing = self._observers.get(root_id)
            if existing:
                old_obs, old_path = existing
                if old_path == path and old_obs.is_alive():
                    return
                try:
                    old_obs.stop()
                    old_obs.join(timeout=3.0)
                except Exception:  # noqa: BLE001
                    logger.exception("failed stopping observer for root %s", root_id)
            handler = _RootHandler(self, root_id, path)
            observer = Observer()
            observer.schedule(handler, str(path), recursive=True)
            observer.start()
            self._observers[root_id] = (observer, path)
            logger.info("watching root %s at %s", root_id, path)

    def unwatch_root(self, root_id: int) -> None:
        with self._lock:
            entry = self._observers.pop(root_id, None)
            # Drop pending for this root
            drop_keys = [k for k, (_, rid, _) in self._pending.items() if rid == root_id]
            for k in drop_keys:
                del self._pending[k]
        if not entry:
            return
        observer, path = entry
        try:
            observer.stop()
            observer.join(timeout=3.0)
        except Exception:  # noqa: BLE001
            logger.exception("failed stopping observer for root %s (%s)", root_id, path)

    def unwatch_by_path(self, root_path: Path | str) -> None:
        path = _abs_str(Path(root_path))
        with self._lock:
            match = [
                rid
                for rid, (_, p) in self._observers.items()
                if _abs_str(p) == path
            ]
        for rid in match:
            self.unwatch_root(rid)

    # --- event intake ---

    def _handle_raw(
        self, root_id: int, root: Path, event: FileSystemEvent
    ) -> None:
        if self._paused:
            return

        etype = event.event_type
        src = _norm(event.src_path)
        dest = _norm(event.dest_path) if getattr(event, "dest_path", None) else None
        is_dir = bool(event.is_directory)

        # Directory creates: children will emit their own file events.
        if etype == "created" and is_dir:
            return

        if etype == "moved":
            if dest is None:
                return
            # Ignore if both sides are junk / outside; if only dest ignored, treat as delete.
            src_ignore = should_ignore_path(src, root=root)
            dest_ignore = should_ignore_path(dest, root=root)
            if is_dir:
                if src_ignore and dest_ignore:
                    return
                if dest_ignore or not path_inside_root(dest, root):
                    change = PendingChange(
                        EventKind.DELETE_TREE, _abs_str(src), is_directory=True
                    )
                elif src_ignore or not path_inside_root(src, root):
                    # Moved into corpus from outside — reconcile via upserts on children
                    # is hard; treat dest tree as needing scan of files that appear.
                    # File events usually follow; skip empty dir.
                    return
                else:
                    change = PendingChange(
                        EventKind.RENAME_TREE,
                        _abs_str(src),
                        dest_path=_abs_str(dest),
                        is_directory=True,
                    )
            else:
                if dest_ignore or should_skip_file(dest.name) or is_temp_basename(dest.name):
                    if not src_ignore:
                        change = PendingChange(EventKind.DELETE, _abs_str(src))
                    else:
                        return
                elif src_ignore:
                    if should_ignore_file_event(dest, root=root):
                        return
                    change = PendingChange(EventKind.UPSERT, _abs_str(dest))
                else:
                    if should_ignore_file_event(dest, root=root):
                        return
                    change = PendingChange(
                        EventKind.RENAME,
                        _abs_str(src),
                        dest_path=_abs_str(dest),
                    )
            self._enqueue(root_id, change)
            return

        if etype in ("deleted",):
            if should_ignore_path(src, root=root):
                return
            if is_dir:
                change = PendingChange(
                    EventKind.DELETE_TREE, _abs_str(src), is_directory=True
                )
            else:
                if should_skip_file(src.name) or is_temp_basename(src.name):
                    return
                change = PendingChange(EventKind.DELETE, _abs_str(src))
            self._enqueue(root_id, change)
            return

        if etype in ("created", "modified", "closed"):
            if is_dir:
                return
            if should_ignore_file_event(src, root=root):
                return
            # Skip if path is not a regular file yet (race) — worker rechecks.
            change = PendingChange(EventKind.UPSERT, _abs_str(src))
            self._enqueue(root_id, change)
            return

    def _enqueue(self, root_id: int, change: PendingChange) -> None:
        # Coalesce key: dest for renames so create+rename storms collapse; else path.
        key = change.dest_path or change.path
        now = time.monotonic()
        with self._lock:
            prev = self._pending.get(key)
            if prev:
                old_change, old_rid, _ = prev
                change = _coalesce(old_change, change)
                root_id = old_rid  # keep original root
                if change is None:
                    del self._pending[key]
                    return
            self._pending[key] = (change, root_id, now)

    # --- worker ---

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            ready = self._take_ready()
            if not ready:
                self._stop.wait(WORKER_POLL_SECONDS)
                continue
            if self._paused:
                # Put back and wait
                with self._lock:
                    for change, root_id, touched in ready:
                        key = change.dest_path or change.path
                        self._pending[key] = (change, root_id, touched)
                self._stop.wait(WORKER_POLL_SECONDS)
                continue
            self._apply_batch(ready)

    def _take_ready(self) -> list[tuple[PendingChange, int, float]]:
        now = time.monotonic()
        ready: list[tuple[PendingChange, int, float]] = []
        with self._lock:
            for key, (change, root_id, touched) in list(self._pending.items()):
                if now - touched >= self._debounce:
                    ready.append((change, root_id, touched))
                    del self._pending[key]
        return ready

    def _apply_batch(self, batch: list[tuple[PendingChange, int, float]]) -> None:
        for change, root_id, _ in batch:
            try:
                self._apply_one(change, root_id)
            except OSError as exc:
                logger.debug("watch apply OSError %s: %s", change, exc)
            except Exception:  # noqa: BLE001
                logger.exception("watch apply failed for %s", change)

    def _apply_one(self, change: PendingChange, root_id: int) -> None:
        if change.kind == EventKind.UPSERT:
            path = Path(change.path)
            if not path.is_file():
                return
            # Re-check root membership after resolve
            with self._lock:
                entry = self._observers.get(root_id)
            if entry and not path_inside_root(path, entry[1]):
                return
            upsert_file(root_id=root_id, path=path)
            return

        if change.kind == EventKind.DELETE:
            delete_file(change.path)
            return

        if change.kind == EventKind.RENAME:
            if not change.dest_path:
                return
            dest = Path(change.dest_path)
            rename_file(change.path, dest, root_id=root_id)
            return

        if change.kind == EventKind.DELETE_TREE:
            delete_files_under_prefix(root_id, change.path)
            return

        if change.kind == EventKind.RENAME_TREE:
            if not change.dest_path:
                return
            rename_files_under_prefix(root_id, change.path, change.dest_path)
            return


def _coalesce(old: PendingChange, new: PendingChange) -> PendingChange | None:
    """Merge two pending ops for the same coalesce key. None = cancel (create+delete)."""
    # Delete cancels prior upsert for same path.
    if new.kind == EventKind.DELETE and old.kind == EventKind.UPSERT:
        if old.path == new.path:
            return None
    if new.kind == EventKind.UPSERT and old.kind == EventKind.DELETE:
        if old.path == new.path:
            return new
    # Rename then upsert dest → keep rename (worker refreshes metadata) or upsert dest
    if old.kind == EventKind.RENAME and new.kind == EventKind.UPSERT:
        if new.path == old.dest_path:
            return old
    if old.kind == EventKind.UPSERT and new.kind == EventKind.RENAME:
        return new
    # Last wins for same kind / tree ops
    return new


# Process-wide singleton used by FastAPI lifespan / routes.
_manager: WatchManager | None = None
_manager_lock = threading.Lock()


def get_watch_manager() -> WatchManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = WatchManager()
        return _manager

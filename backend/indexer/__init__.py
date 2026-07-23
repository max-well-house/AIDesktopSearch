from indexer.metadata import index_status, replace_root_files, ensure_root
from indexer.scan import iter_files

__all__ = [
    "ensure_root",
    "index_status",
    "iter_files",
    "replace_root_files",
    "scan_and_save",
]


def scan_and_save(folder: str) -> dict:
    """Walk folder, persist metadata, return scan summary (#41)."""
    from pathlib import Path

    root_path = Path(folder).expanduser().resolve()
    root_id = ensure_root(root_path)
    files = iter_files(root_path)
    upserted, removed = replace_root_files(root_id, files)
    status = index_status()
    return {
        "root_id": root_id,
        "root_path": str(root_path),
        "files_upserted": upserted,
        "files_removed": removed,
        "file_count": status["file_count"],
        "root_count": status["root_count"],
        "last_indexed_at": status["last_indexed_at"],
    }

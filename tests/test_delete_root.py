"""Unit tests for corpus root delete (#40)."""

from pathlib import Path

import pytest

from db import init_db
from db.connection import connect
from indexer import delete_root, ensure_root, index_status, replace_root_files


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test-index.db"
    monkeypatch.setenv("AIDESKTOP_DB", str(db_path))
    init_db(db_path)
    return db_path


def _checkpoint(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def _db_payload(db_path: Path) -> bytes:
    """Main DB + WAL/SHM (WAL mode may keep recent rows off the main file)."""
    data = db_path.read_bytes()
    for suffix in ("-wal", "-shm"):
        side = Path(f"{db_path}{suffix}")
        if side.exists():
            data += side.read_bytes()
    return data


def test_delete_root_removes_files_and_root(temp_db, tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    file_a = folder / "a.txt"
    file_a.write_text("hello", encoding="utf-8")

    root_id = ensure_root(folder)
    replace_root_files(root_id, [file_a])

    before = index_status()
    assert before["root_count"] == 1
    assert before["file_count"] == 1

    result = delete_root(root_id)
    assert result is not None
    assert result["root_id"] == root_id
    assert result["files_removed"] == 1
    assert result["root_count"] == 0
    assert result["file_count"] == 0

    after = index_status()
    assert after["roots"] == []


def test_delete_root_missing_returns_none(temp_db):
    assert delete_root(999) is None


def test_delete_root_vacuums_path_out_of_db_file(temp_db, tmp_path):
    """Light wipe: VACUUM should drop deleted path strings from free pages."""
    folder = tmp_path / "SensitiveSecrets"
    folder.mkdir()
    file_a = folder / "payroll.txt"
    file_a.write_text("secret", encoding="utf-8")

    root_id = ensure_root(folder)
    replace_root_files(root_id, [file_a])
    _checkpoint(temp_db)

    root_path = str(folder.resolve())
    path_bytes = root_path.encode("utf-8")
    assert path_bytes in _db_payload(temp_db)

    delete_root(root_id)

    assert path_bytes not in _db_payload(temp_db)
    assert b"payroll.txt" not in _db_payload(temp_db)

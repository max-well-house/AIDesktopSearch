"""Per-root auto_watch (#118) and index wipe (#114)."""

from __future__ import annotations

from db import connect, init_db
from db.schema import SCHEMA_VERSION
from indexer import ensure_root, index_status, set_root_auto_watch, wipe_index_database
from indexer.metadata import replace_root_files


def test_schema_version_four_has_auto_watch(tmp_path, monkeypatch):
    db_path = tmp_path / "index.db"
    monkeypatch.setenv("AIDESKTOP_DB", str(db_path))
    init_db(db_path)
    with connect() as conn:
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        cols = {row[1] for row in conn.execute("PRAGMA table_info(roots)").fetchall()}
    assert version == SCHEMA_VERSION
    assert "auto_watch" in cols


def test_set_root_auto_watch(tmp_path, monkeypatch):
    db_path = tmp_path / "index.db"
    monkeypatch.setenv("AIDESKTOP_DB", str(db_path))
    init_db(db_path)
    folder = tmp_path / "corpus"
    folder.mkdir()
    root_id = ensure_root(folder)
    status = index_status()
    assert status["roots"][0]["auto_watch"] is True

    updated = set_root_auto_watch(root_id, False)
    assert updated is not None
    assert updated["auto_watch"] is False
    assert index_status()["roots"][0]["auto_watch"] is False

    again = set_root_auto_watch(root_id, True)
    assert again["auto_watch"] is True


def test_wipe_index_recreates_empty(tmp_path, monkeypatch):
    db_path = tmp_path / "index.db"
    monkeypatch.setenv("AIDESKTOP_DB", str(db_path))
    init_db(db_path)
    folder = tmp_path / "corpus"
    folder.mkdir()
    note = folder / "note.txt"
    note.write_text("hello", encoding="utf-8")
    root_id = ensure_root(folder)
    replace_root_files(root_id, [note])
    assert index_status()["file_count"] >= 1
    assert db_path.is_file()

    result = wipe_index_database()
    assert result["ok"] is True
    assert result["file_count"] == 0
    assert result["root_count"] == 0
    assert db_path.is_file()
    assert note.is_file()  # original file untouched
    with connect() as conn:
        assert int(conn.execute("PRAGMA user_version").fetchone()[0]) == SCHEMA_VERSION


def test_wipe_drops_vec_chunks_so_reembed_works(tmp_path, monkeypatch):
    """#114 regression: orphan vec_chunks PKs must not block re-embed after wipe."""
    from embeddings.store import (
        DEFAULT_EMBED_DIM,
        ChunkRecord,
        replace_file_embeddings,
        vector_store_status,
    )

    db_path = tmp_path / "index.db"
    monkeypatch.setenv("AIDESKTOP_DB", str(db_path))
    init_db(db_path)
    folder = tmp_path / "corpus"
    folder.mkdir()
    note = folder / "note.txt"
    note.write_text("Piplup is a water-type starter.", encoding="utf-8")
    root_id = ensure_root(folder)
    replace_root_files(root_id, [note])
    with connect() as conn:
        file_id = int(conn.execute("SELECT id FROM files LIMIT 1").fetchone()["id"])

    vec = [0.0] * DEFAULT_EMBED_DIM
    vec[0] = 1.0
    replace_file_embeddings(
        file_id,
        [ChunkRecord(chunk_index=0, embedding=vec, page=1, text_preview="piplup")],
    )
    assert vector_store_status()["chunk_count"] == 1

    wipe_index_database()
    assert index_status()["file_count"] == 0

    # Re-add and embed again — must not UNIQUE-fail on vec_chunks.
    root_id = ensure_root(folder)
    replace_root_files(root_id, [note])
    with connect() as conn:
        file_id = int(conn.execute("SELECT id FROM files LIMIT 1").fetchone()["id"])
    n = replace_file_embeddings(
        file_id,
        [ChunkRecord(chunk_index=0, embedding=vec, page=1, text_preview="piplup")],
    )
    assert n == 1
    assert vector_store_status()["chunk_count"] == 1

"""Embedding store + sqlite-vec (#67 / Decision #008)."""

from __future__ import annotations

import pytest

from db import connect, init_db
from embeddings.store import (
    DEFAULT_EMBED_DIM,
    ChunkRecord,
    clear_file_embeddings,
    knn_chunks,
    replace_file_embeddings,
    run_store_smoke,
    vector_store_status,
)
from indexer import ensure_root, replace_root_files


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test-index.db"
    monkeypatch.setenv("AIDESKTOP_DB", str(db_path))
    init_db(db_path)
    return db_path


def _unit_vec(seed: float = 1.0) -> list[float]:
    vec = [0.0] * DEFAULT_EMBED_DIM
    vec[0] = float(seed)
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [x / norm for x in vec]


def test_vector_store_loads(temp_db):
    status = vector_store_status()
    assert status["available"] is True
    assert status["version"]
    assert status["dimension"] == DEFAULT_EMBED_DIM
    assert status["chunk_count"] == 0


def test_replace_and_knn(temp_db, tmp_path):
    folder = tmp_path / "corpus"
    folder.mkdir()
    path = folder / "a.txt"
    path.write_text("hello", encoding="utf-8")
    root_id = ensure_root(folder)
    replace_root_files(root_id, [path])
    with connect() as conn:
        file_id = int(conn.execute("SELECT id FROM files LIMIT 1").fetchone()["id"])

    a = _unit_vec(1.0)
    b = _unit_vec(0.5)
    # Second file vector slightly different
    b[1] = 0.1
    norm = sum(x * x for x in b) ** 0.5
    b = [x / norm for x in b]

    n = replace_file_embeddings(
        file_id,
        [
            ChunkRecord(chunk_index=0, embedding=a, page=1, text_preview="alpha"),
            ChunkRecord(chunk_index=1, embedding=b, page=1, text_preview="beta"),
        ],
    )
    assert n == 2
    assert vector_store_status()["chunk_count"] == 2

    hits = knn_chunks(a, k=2)
    assert len(hits) >= 1
    assert hits[0]["text_preview"] == "alpha"
    assert hits[0]["distance"] == pytest.approx(0.0, abs=1e-5)

    clear_file_embeddings(file_id)
    assert vector_store_status()["chunk_count"] == 0
    assert knn_chunks(a, k=2) == []


def test_store_smoke_round_trip(temp_db, tmp_path):
    folder = tmp_path / "corpus"
    folder.mkdir()
    path = folder / "b.txt"
    path.write_text("smoke", encoding="utf-8")
    root_id = ensure_root(folder)
    replace_root_files(root_id, [path])
    result = run_store_smoke()
    assert result["ok"] is True
    assert result["distance"] == pytest.approx(0.0, abs=1e-5)
    # Smoke cleans up after itself.
    assert vector_store_status()["chunk_count"] == 0


def test_smoke_needs_files(temp_db):
    result = run_store_smoke()
    assert result["ok"] is False
    assert "file" in (result.get("error") or "").lower()

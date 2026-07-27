"""Chunker + generate path (#66)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from db import connect, init_db
from embeddings.chunk import CHUNK_OVERLAP, CHUNK_SIZE, chunk_pages, chunk_text
from embeddings.generate import embed_file, list_pending_embed_file_ids
from embeddings.queue import EmbedQueue
from embeddings.store import DEFAULT_EMBED_DIM, vector_store_status
from indexer import ensure_root, replace_root_files
from indexer.content import sync_file_content


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test-index.db"
    monkeypatch.setenv("AIDESKTOP_DB", str(db_path))
    init_db(db_path)
    return db_path


def test_chunk_text_overlap():
    text = "a" * (CHUNK_SIZE + 50)
    chunks = chunk_text(text, page=1)
    assert len(chunks) >= 2
    assert chunks[0].chunk_index == 0
    assert chunks[0].page == 1
    assert len(chunks[0].text) <= CHUNK_SIZE
    # Overlap means second window starts before first ends.
    assert CHUNK_OVERLAP > 0


def test_chunk_pages_global_index():
    pages = [(1, "hello " * 20), (2, "world " * 20)]
    chunks = chunk_pages(pages, chunk_size=40, overlap=8)
    assert chunks
    indexes = [c.chunk_index for c in chunks]
    assert indexes == list(range(len(chunks)))
    assert {c.page for c in chunks} <= {1, 2}


def test_list_pending_and_embed_file(temp_db, tmp_path):
    folder = tmp_path / "corpus"
    folder.mkdir()
    path = folder / "note.txt"
    path.write_text("Piplup is a water-type starter Pokemon.", encoding="utf-8")
    root_id = ensure_root(folder)
    replace_root_files(root_id, [path])
    with connect() as conn:
        file_id = int(conn.execute("SELECT id FROM files LIMIT 1").fetchone()["id"])
    sync_file_content(file_id, path, path.stat().st_mtime)

    pending = list_pending_embed_file_ids()
    assert file_id in pending

    def fake_embed_texts(texts, **_kwargs):
        return [[0.01] * DEFAULT_EMBED_DIM for _ in texts]

    with (
        patch("embeddings.generate.model_available", return_value=True),
        patch("embeddings.generate.embed_texts", side_effect=fake_embed_texts) as mock_embed,
    ):
        result = embed_file(file_id)
    assert result["status"] == "ok"
    assert result["chunks"] >= 1
    assert mock_embed.called
    assert vector_store_status()["chunk_count"] >= 1
    assert list_pending_embed_file_ids() == []


def test_embed_queue_pause(temp_db):
    done: list[int] = []

    def fake_embed(fid: int) -> dict:
        done.append(fid)
        return {"file_id": fid, "status": "ok", "chunks": 1}

    q = EmbedQueue(embed_fn=fake_embed, poll_seconds=0.05)
    q.pause()
    q.start()
    q.enqueue(1)
    q.enqueue(2)
    import time

    time.sleep(0.2)
    assert done == []
    assert q.status()["queue_depth"] == 2
    q.resume()
    deadline = time.time() + 2
    while time.time() < deadline and q.status()["queue_depth"] > 0:
        time.sleep(0.05)
    q.stop()
    assert sorted(done) == [1, 2]

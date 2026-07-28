"""Semantic search endpoint (#68)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from db import connect, init_db
from embeddings.store import DEFAULT_EMBED_DIM, ChunkRecord, replace_file_embeddings
from indexer import ensure_root, replace_root_files
from indexer.content import sync_file_content
from search import execute_search, run_semantic


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test-index.db"
    monkeypatch.setenv("AIDESKTOP_DB", str(db_path))
    init_db(db_path)
    return db_path


def _unit_vec(axis: int = 0) -> list[float]:
    vec = [0.0] * DEFAULT_EMBED_DIM
    vec[axis] = 1.0
    return vec


@pytest.fixture()
def corpus_with_vectors(temp_db, tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    path = folder / "earnings-notes.md"
    path.write_text(
        "Q3 revenue summary and quarterly earnings discussion.",
        encoding="utf-8",
    )
    other = folder / "recipes.txt"
    other.write_text("chocolate chip cookies", encoding="utf-8")
    root_id = ensure_root(folder)
    replace_root_files(root_id, [path, other])
    with connect() as conn:
        rows = {
            row["name"]: int(row["id"])
            for row in conn.execute("SELECT id, name FROM files")
        }
    sync_file_content(rows["earnings-notes.md"], path, path.stat().st_mtime)
    sync_file_content(rows["recipes.txt"], other, other.stat().st_mtime)

    replace_file_embeddings(
        rows["earnings-notes.md"],
        [
            ChunkRecord(
                chunk_index=0,
                embedding=_unit_vec(0),
                page=1,
                text_preview="Q3 revenue",
            )
        ],
    )
    replace_file_embeddings(
        rows["recipes.txt"],
        [
            ChunkRecord(
                chunk_index=0,
                embedding=_unit_vec(1),
                page=1,
                text_preview="cookies",
            )
        ],
    )
    return rows


def test_run_semantic_maps_nearest_file(corpus_with_vectors):
    with patch("embeddings.client.embed_texts", return_value=[_unit_vec(0)]):
        hits = run_semantic("quarterly revenue")
    assert len(hits) >= 1
    assert hits[0]["name"] == "earnings-notes.md"
    assert hits[0]["match"] == "semantic"


def test_execute_search_mode_semantic(corpus_with_vectors):
    with patch("embeddings.client.embed_texts", return_value=[_unit_vec(0)]):
        payload = execute_search("meaning query", mode="semantic")
    assert payload["mode"] == "semantic"
    assert "classic" in payload["stages_skipped"]
    assert payload["results"][0]["name"] == "earnings-notes.md"


def test_execute_search_auto_salvages_empty_classic(corpus_with_vectors, monkeypatch):
    monkeypatch.setattr("search.routing.run_classic", lambda *_a, **_k: [])
    with patch("embeddings.client.embed_texts", return_value=[_unit_vec(0)]):
        payload = execute_search("earnings performance outlook", mode="auto")
    assert payload["mode"] == "semantic"
    assert payload["count"] >= 1
    assert payload["results"][0]["match"] == "semantic"


def test_execute_search_classic_unchanged(corpus_with_vectors):
    payload = execute_search("recipes", mode="classic")
    assert payload["mode"] == "classic"
    assert payload["stages_skipped"] == ["semantic", "llm"]
    assert any(h["name"] == "recipes.txt" for h in payload["results"])


def test_get_search_mode_semantic(corpus_with_vectors):
    from main import app

    client = TestClient(app)
    with patch("embeddings.client.embed_texts", return_value=[_unit_vec(0)]):
        response = client.get(
            "/search",
            params={"q": "quarterly revenue", "mode": "semantic"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "semantic"
    assert body["count"] >= 1
    assert body["results"][0]["match"] == "semantic"


def test_run_semantic_soft_fails_without_ollama(corpus_with_vectors):
    from embeddings.client import EmbedClientError

    with patch(
        "embeddings.client.embed_texts",
        side_effect=EmbedClientError("down"),
    ):
        assert run_semantic("anything") == []


def test_run_semantic_applies_distance_floor(corpus_with_vectors, monkeypatch):
    """Weak neighbors above SEMANTIC_MAX_DISTANCE are dropped; nearest kept."""
    from search.routing import SEMANTIC_MAX_DISTANCE

    near = {
        "chunk_id": 1,
        "file_id": corpus_with_vectors["earnings-notes.md"],
        "page": 1,
        "chunk_index": 0,
        "distance": 0.2,
        "text_preview": "Q3",
    }
    far = {
        "chunk_id": 2,
        "file_id": corpus_with_vectors["recipes.txt"],
        "page": 1,
        "chunk_index": 0,
        "distance": SEMANTIC_MAX_DISTANCE + 0.2,
        "text_preview": "cookies",
    }
    monkeypatch.setattr(
        "embeddings.store.knn_chunks",
        lambda *_a, **_k: [near, far],
    )
    with patch("embeddings.client.embed_texts", return_value=[_unit_vec(0)]):
        hits = run_semantic("quarterly revenue")
    names = [h["name"] for h in hits]
    assert "earnings-notes.md" in names
    assert "recipes.txt" not in names


def test_run_semantic_keeps_nearest_when_all_above_floor(corpus_with_vectors, monkeypatch):
    from search.routing import SEMANTIC_MAX_DISTANCE

    only = {
        "chunk_id": 1,
        "file_id": corpus_with_vectors["earnings-notes.md"],
        "page": 1,
        "chunk_index": 0,
        "distance": SEMANTIC_MAX_DISTANCE + 0.3,
        "text_preview": "Q3",
    }
    monkeypatch.setattr(
        "embeddings.store.knn_chunks",
        lambda *_a, **_k: [only],
    )
    with patch("embeddings.client.embed_texts", return_value=[_unit_vec(0)]):
        hits = run_semantic("obscure query")
    assert len(hits) == 1
    assert hits[0]["name"] == "earnings-notes.md"

"""Query routing + hybrid merge (#98 / #69)."""

import pytest
from fastapi.testclient import TestClient

from db import init_db
from indexer import ensure_root, replace_root_files
from search import (
    classify_query,
    execute_search,
    is_filename_like,
    merge_hybrid_results,
    run_llm,
)


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test-index.db"
    monkeypatch.setenv("AIDESKTOP_DB", str(db_path))
    init_db(db_path)
    return db_path


@pytest.fixture()
def seeded_index(temp_db, tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    files = [
        folder / "invoice.pdf",
        folder / "Invoice-Acme.pdf",
        folder / "notes.txt",
    ]
    for path in files:
        path.write_text("x", encoding="utf-8")

    root_id = ensure_root(folder)
    replace_root_files(root_id, files)
    return folder


def test_filename_like_and_classify():
    assert is_filename_like("invoice.pdf")
    assert is_filename_like("Charizard")
    assert is_filename_like("Shopping List")
    assert classify_query("Invoice") == "classic"
    assert classify_query("invoice.pdf") == "classic"
    assert classify_query("") == "classic"
    assert classify_query("fire dragon pokemon") == "hybrid"
    assert classify_query("summarize my Q3 budget notes") == "hybrid"
    assert classify_query("what is in the earnings report") == "hybrid"


def test_merge_hybrid_classic_wins_overlap():
    classic = [
        {
            "id": 1,
            "path": "/a/invoice.pdf",
            "name": "invoice.pdf",
            "match": "filename",
            "page": None,
        }
    ]
    semantic = [
        {
            "id": 1,
            "path": "/a/invoice.pdf",
            "name": "invoice.pdf",
            "match": "semantic",
            "page": 2,
        },
        {
            "id": 2,
            "path": "/a/other.md",
            "name": "other.md",
            "match": "semantic",
            "page": 1,
        },
    ]
    merged = merge_hybrid_results(classic, semantic, limit=10)
    assert [h["id"] for h in merged] == [1, 2]
    assert merged[0]["match"] == "hybrid"
    assert merged[0]["page"] == 2
    assert merged[1]["match"] == "semantic"


def test_execute_search_returns_classic_hits(seeded_index):
    payload = execute_search("Invoice", mode="classic")
    assert payload["mode"] == "classic"
    assert payload["stages_skipped"] == ["semantic", "llm"]
    names = {h["name"] for h in payload["results"]}
    assert "invoice.pdf" in names
    assert payload["count"] == len(payload["results"])


def test_execute_search_empty_query(seeded_index):
    payload = execute_search("   ", mode="auto")
    assert payload["results"] == []
    assert payload["count"] == 0
    assert payload["mode"] == "classic"


def test_auto_filename_like_skips_semantic(seeded_index, monkeypatch):
    def boom_semantic(*_args, **_kwargs):
        raise AssertionError("run_semantic must not run for filename-like auto")

    monkeypatch.setattr("search.routing.run_semantic", boom_semantic)
    payload = execute_search("invoice.pdf", mode="auto")
    assert payload["mode"] == "classic"
    assert len(payload["results"]) >= 1


def test_semantic_and_llm_hooks_not_called_on_classic(seeded_index, monkeypatch):
    def boom_semantic(*_args, **_kwargs):
        raise AssertionError("run_semantic must not be called on classic mode")

    def boom_llm(*_args, **_kwargs):
        raise AssertionError("run_llm must not be called yet")

    monkeypatch.setattr("search.routing.run_semantic", boom_semantic)
    monkeypatch.setattr("search.routing.run_llm", boom_llm)
    payload = execute_search("Invoice", mode="classic")
    assert payload["mode"] == "classic"
    assert len(payload["results"]) >= 1


def test_stub_llm_returns_none():
    assert run_llm("anything") is None


def test_get_search_reports_mode(seeded_index):
    from main import app

    client = TestClient(app)
    response = client.get("/search", params={"q": "Invoice", "mode": "classic"})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "classic"
    assert body["stages_skipped"] == ["semantic", "llm"]
    assert body["count"] >= 2


def test_auto_hybrid_merges(seeded_index, monkeypatch):
    classic = [
        {
            "id": 10,
            "path": "/x/a.pdf",
            "name": "a.pdf",
            "extension": "pdf",
            "size": 1,
            "mtime": 1.0,
            "root_id": 1,
            "page": None,
            "match": "filename",
        }
    ]
    semantic = [
        {
            "id": 20,
            "path": "/x/b.md",
            "name": "b.md",
            "extension": "md",
            "size": 1,
            "mtime": 1.0,
            "root_id": 1,
            "page": 1,
            "match": "semantic",
        }
    ]
    monkeypatch.setattr("search.routing.run_classic", lambda *_a, **_k: classic)
    monkeypatch.setattr("search.routing.run_semantic", lambda *_a, **_k: semantic)
    monkeypatch.setattr("search.routing._vectors_ready", lambda: True)
    monkeypatch.setattr(
        "search.routing.classify_query", lambda *_a, **_k: "hybrid"
    )
    payload = execute_search("fire dragon pokemon creature", mode="auto")
    assert payload["mode"] == "hybrid"
    assert payload["stages_skipped"] == ["llm"]
    assert [h["id"] for h in payload["results"]] == [10, 20]

"""Unit tests for hybrid query routing stub (#98)."""

import pytest
from fastapi.testclient import TestClient

from db import init_db
from indexer import ensure_root, replace_root_files
from search import classify_query, execute_search, run_llm, run_semantic


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


def test_classify_always_classic():
    assert classify_query("Invoice") == "classic"
    assert classify_query("summarize my Q3 budget PDF") == "classic"
    assert classify_query("") == "classic"


def test_execute_search_returns_classic_hits(seeded_index):
    payload = execute_search("Invoice")
    assert payload["mode"] == "classic"
    assert payload["stages_skipped"] == ["semantic", "llm"]
    names = {h["name"] for h in payload["results"]}
    assert "invoice.pdf" in names
    assert payload["count"] == len(payload["results"])


def test_execute_search_empty_query(seeded_index):
    payload = execute_search("   ")
    assert payload["results"] == []
    assert payload["count"] == 0
    assert payload["mode"] == "classic"


def test_semantic_and_llm_hooks_not_called(seeded_index, monkeypatch):
    def boom_semantic(*_args, **_kwargs):
        raise AssertionError("run_semantic must not be called on stub path")

    def boom_llm(*_args, **_kwargs):
        raise AssertionError("run_llm must not be called on stub path")

    monkeypatch.setattr("search.routing.run_semantic", boom_semantic)
    monkeypatch.setattr("search.routing.run_llm", boom_llm)
    payload = execute_search("Invoice")
    assert payload["mode"] == "classic"
    assert len(payload["results"]) >= 1


def test_stub_hooks_return_empty():
    assert run_semantic("anything") == []
    assert run_llm("anything") is None


def test_get_search_reports_mode(seeded_index):
    from main import app

    client = TestClient(app)
    response = client.get("/search", params={"q": "Invoice"})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "classic"
    assert body["stages_skipped"] == ["semantic", "llm"]
    assert body["count"] >= 2

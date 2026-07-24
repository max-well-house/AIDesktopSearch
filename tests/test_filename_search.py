"""Unit tests for classic filename search (#42)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from db import init_db
from indexer import ensure_root, replace_root_files, search_filenames


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
        folder / "report_final.docx",
        folder / "100%_done.txt",
    ]
    for path in files:
        path.write_text("x", encoding="utf-8")

    root_id = ensure_root(folder)
    replace_root_files(root_id, files)
    return folder


def test_invoice_query_finds_invoice_pdf(seeded_index):
    hits = search_filenames("Invoice")
    names = {h["name"] for h in hits}
    assert "invoice.pdf" in names
    assert "Invoice-Acme.pdf" in names
    assert "notes.txt" not in names


def test_lowercase_query_is_case_insensitive(seeded_index):
    hits = search_filenames("invoice")
    names = {h["name"] for h in hits}
    assert "invoice.pdf" in names
    assert "Invoice-Acme.pdf" in names


def test_empty_query_returns_no_rows(seeded_index):
    assert search_filenames("") == []
    assert search_filenames("   ") == []


def test_like_metacharacters_are_literal(seeded_index):
    hits = search_filenames("100%")
    names = [h["name"] for h in hits]
    assert names == ["100%_done.txt"]


def test_prefix_hits_rank_before_substring(seeded_index):
    hits = search_filenames("invoice")
    assert hits[0]["name"].lower().startswith("invoice")


def test_get_search_endpoint(seeded_index):
    from main import app

    client = TestClient(app)
    response = client.get("/search", params={"q": "Invoice"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "Invoice"
    assert body["count"] >= 2
    names = {r["name"] for r in body["results"]}
    assert "invoice.pdf" in names

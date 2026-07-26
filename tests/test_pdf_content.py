"""PDF extract + content sync (#54 / #58)."""

from pathlib import Path

import pytest

from db import connect, init_db
from indexer import ensure_root, replace_root_files
from indexer.content import sync_pdf_content, sync_pdfs_for_root
from indexer.pdf_extract import extract_pdf


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test-index.db"
    monkeypatch.setenv("AIDESKTOP_DB", str(db_path))
    init_db(db_path)
    return db_path


def _write_text_pdf(path: Path, pages: list[str]) -> Path:
    import pymupdf

    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()
    return path


def test_extract_pdf_ok_per_page(tmp_path: Path):
    pdf = _write_text_pdf(tmp_path / "a.pdf", ["hello page one", "world page two"])
    result = extract_pdf(pdf)
    assert result.status == "ok"
    assert result.page_count == 2
    assert len(result.pages) == 2
    assert "hello" in result.pages[0][1]
    assert "world" in result.pages[1][1]


def test_extract_timeout_soft_fails(tmp_path: Path):
    pdf = _write_text_pdf(tmp_path / "slow.pdf", [f"page {i}" for i in range(5)])
    result = extract_pdf(pdf, max_seconds=0)
    assert result.status == "error"
    assert any("exceeded" in w for w in result.warnings)
    assert result.pages == []


def test_sync_pdf_content_writes_fts_and_skips_same_mtime(temp_db, tmp_path: Path):
    pdf = _write_text_pdf(tmp_path / "docs" / "note.pdf", ["invoice total due"])
    root_id = ensure_root(tmp_path / "docs")
    replace_root_files(root_id, [pdf])

    with connect() as conn:
        row = conn.execute(
            "SELECT id, mtime FROM files WHERE path = ?",
            (str(pdf.resolve()),),
        ).fetchone()
        file_id = int(row["id"])
        mtime = float(row["mtime"])
        pages = conn.execute(
            "SELECT page, text FROM file_pages_fts WHERE file_id = ? ORDER BY page",
            (file_id,),
        ).fetchall()
        content = conn.execute(
            "SELECT status, mtime_at_parse, parsed_at FROM file_content WHERE file_id = ?",
            (file_id,),
        ).fetchone()

    assert content["status"] == "ok"
    assert float(content["mtime_at_parse"]) == mtime
    assert len(pages) >= 1
    assert "invoice" in pages[0]["text"].lower()
    parsed_at = content["parsed_at"]

    # Second sync with same mtime must skip re-extract.
    sync_pdf_content(file_id, pdf, mtime)
    with connect() as conn:
        again = conn.execute(
            "SELECT status, mtime_at_parse, parsed_at FROM file_content WHERE file_id = ?",
            (file_id,),
        ).fetchone()
        fts_count = conn.execute(
            "SELECT COUNT(*) AS n FROM file_pages_fts WHERE file_id = ?",
            (file_id,),
        ).fetchone()["n"]

    assert again["status"] == "ok"
    assert float(again["mtime_at_parse"]) == mtime
    assert again["parsed_at"] == parsed_at
    assert fts_count >= 1


def test_sync_pdfs_for_root_batch(temp_db, tmp_path: Path):
    folder = tmp_path / "corpus"
    pdfs = [
        _write_text_pdf(folder / f"doc{i}.pdf", [f"alpha{i} content"])
        for i in range(3)
    ]
    root_id = ensure_root(folder)
    replace_root_files(root_id, pdfs)

    with connect() as conn:
        n_content = conn.execute("SELECT COUNT(*) AS n FROM file_content").fetchone()[
            "n"
        ]
        n_fts = conn.execute("SELECT COUNT(*) AS n FROM file_pages_fts").fetchone()["n"]
    assert n_content == 3
    assert n_fts >= 3

    # Idempotent second pass (mtime skip).
    sync_pdfs_for_root(root_id)
    with connect() as conn:
        assert (
            conn.execute("SELECT COUNT(*) AS n FROM file_content").fetchone()["n"] == 3
        )

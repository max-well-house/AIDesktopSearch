"""Markdown extract + content sync (#61)."""

from pathlib import Path

import pytest

from db import connect, init_db
from indexer import ensure_root, replace_root_files
from indexer.extract import extract_for_path
from indexer.markdown_extract import extract_md
from indexer.search import search_filenames


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test-index.db"
    monkeypatch.setenv("AIDESKTOP_DB", str(db_path))
    init_db(db_path)
    return db_path


def test_extract_md_preserves_headings(tmp_path: Path):
    path = tmp_path / "notes.md"
    path.write_text(
        "# Phoenix Plan\n\n- ship search\n- unique token torterra\n",
        encoding="utf-8",
    )
    result = extract_md(path)
    assert result.status == "ok"
    assert result.parser == "stdlib-md"
    assert result.page_count == 1
    body = result.pages[0][1]
    assert "# Phoenix Plan" in body
    assert "torterra" in body


def test_extract_markdown_extension(tmp_path: Path):
    path = tmp_path / "readme.markdown"
    path.write_text("## Heading\n\nbody totodile\n", encoding="utf-8")
    result = extract_for_path(path)
    assert result.status == "ok"
    assert result.parser == "stdlib-md"
    assert "totodile" in result.pages[0][1]


def test_md_sync_and_search(temp_db, tmp_path: Path):
    folder = tmp_path / "docs"
    folder.mkdir()
    path = folder / "phoenix.md"
    path.write_text(
        "# Phoenix\n\nFilename is phoenix; body has unique token **groudon**.\n",
        encoding="utf-8",
    )
    root_id = ensure_root(folder)
    replace_root_files(root_id, [path])

    with connect() as conn:
        file_id = int(
            conn.execute(
                "SELECT id FROM files WHERE path = ?",
                (str(path.resolve()),),
            ).fetchone()["id"]
        )
        content = conn.execute(
            "SELECT status, parser, page_count FROM file_content WHERE file_id = ?",
            (file_id,),
        ).fetchone()
        pages = conn.execute(
            "SELECT page, text FROM file_pages_fts WHERE file_id = ?",
            (file_id,),
        ).fetchall()

    assert content["status"] == "ok"
    assert content["parser"] == "stdlib-md"
    assert int(content["page_count"]) == 1
    assert len(pages) == 1
    assert "# Phoenix" in pages[0]["text"]
    assert "groudon" in pages[0]["text"].lower()

    hits = search_filenames("groudon")
    assert len(hits) == 1
    assert hits[0]["name"] == "phoenix.md"
    assert hits[0]["match"] in ("content", "both")
    assert hits[0]["page"] == 1
    assert hits[0]["extension"] == "md"

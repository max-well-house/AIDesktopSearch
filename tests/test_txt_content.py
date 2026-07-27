"""TXT extract + content sync (#60)."""

from pathlib import Path

import pytest

from db import connect, init_db
from indexer import ensure_root, replace_root_files
from indexer.extract import extract_for_path
from indexer.search import search_filenames
from indexer.text_extract import extract_txt


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test-index.db"
    monkeypatch.setenv("AIDESKTOP_DB", str(db_path))
    init_db(db_path)
    return db_path


def test_extract_txt_utf8(tmp_path: Path):
    path = tmp_path / "note.txt"
    path.write_text("hello piplup world\n", encoding="utf-8")
    result = extract_txt(path)
    assert result.status == "ok"
    assert result.parser == "stdlib-txt"
    assert result.page_count == 1
    assert result.pages == [(1, "hello piplup world\n")]


def test_extract_txt_utf8_bom(tmp_path: Path):
    path = tmp_path / "bom.txt"
    path.write_text("bom marker\n", encoding="utf-8-sig")
    result = extract_txt(path)
    assert result.status == "ok"
    assert "bom marker" in result.pages[0][1]
    assert not result.pages[0][1].startswith("\ufeff")


def test_extract_txt_cp1252(tmp_path: Path):
    # 0xA9 is © in cp1252; not valid utf-8 alone.
    path = tmp_path / "win.txt"
    path.write_bytes(b"copyright \xa9 2026\n")
    result = extract_txt(path)
    assert result.status == "ok"
    assert "\xa9" in result.pages[0][1] or "©" in result.pages[0][1]
    assert any("cp1252" in w for w in result.warnings)


def test_extract_txt_empty(tmp_path: Path):
    path = tmp_path / "empty.txt"
    path.write_bytes(b"")
    result = extract_txt(path)
    assert result.status == "empty"
    assert result.pages == []


def test_extract_for_path_dispatches_txt(tmp_path: Path):
    path = tmp_path / "via.txt"
    path.write_text("registry txt", encoding="utf-8")
    result = extract_for_path(path)
    assert result.status == "ok"
    assert result.parser == "stdlib-txt"


def test_txt_sync_and_search(temp_db, tmp_path: Path):
    folder = tmp_path / "docs"
    folder.mkdir()
    path = folder / "charizard.txt"
    path.write_text(
        "The title is Charizard but the body mentions piplup uniquely.\n",
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
    assert content["parser"] == "stdlib-txt"
    assert int(content["page_count"]) == 1
    assert len(pages) == 1
    assert pages[0]["page"] == 1
    assert "piplup" in pages[0]["text"].lower()

    hits = search_filenames("piplup")
    assert len(hits) == 1
    assert hits[0]["name"] == "charizard.txt"
    assert hits[0]["match"] in ("content", "both")
    assert hits[0]["page"] == 1
    assert hits[0]["extension"] == "txt"

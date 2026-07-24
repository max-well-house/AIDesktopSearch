"""Unit tests for scan ignore rules (#45 hidden, #46 node_modules / denylist)."""

from pathlib import Path

from indexer.ignore import (
    DEFAULT_SKIP_DIR_NAMES,
    is_hidden_name,
    should_skip_dir,
    should_skip_file,
)
from indexer.scan import iter_files


def _touch(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_default_skip_dirs_include_node_modules_and_vcs():
    assert "node_modules" in DEFAULT_SKIP_DIR_NAMES
    assert ".git" in DEFAULT_SKIP_DIR_NAMES


def test_is_hidden_name():
    assert is_hidden_name(".hidden")
    assert is_hidden_name(".git")
    assert not is_hidden_name("visible")
    assert not is_hidden_name("node_modules")


def test_should_skip_dir_denylist_and_hidden():
    assert should_skip_dir("node_modules")
    assert should_skip_dir(".cache")
    assert not should_skip_dir("Documents")
    assert should_skip_dir("IgnoreMe", extra_skip_dirs=["IgnoreMe"])
    assert not should_skip_dir("IgnoreMe")


def test_should_skip_file_dotfiles():
    assert should_skip_file(".env")
    assert not should_skip_file("readme.txt")
    assert not should_skip_file(".env", skip_hidden=False)


def test_iter_files_skips_hidden_dirs_and_dotfiles(tmp_path: Path):
    keep = _touch(tmp_path / "docs" / "invoice.pdf")
    _touch(tmp_path / ".hidden" / "secret.txt")
    _touch(tmp_path / "docs" / ".env")
    _touch(tmp_path / "docs" / ".cache" / "tmp.bin")

    found = {p.resolve() for p in iter_files(tmp_path)}
    assert keep.resolve() in found
    assert all(".hidden" not in p.parts for p in found)
    assert all(p.name != ".env" for p in found)
    assert all(".cache" not in p.parts for p in found)


def test_iter_files_skips_node_modules_at_any_depth(tmp_path: Path):
    keep = _touch(tmp_path / "Projects" / "Phoenix" / "readme.md")
    _touch(tmp_path / "node_modules" / "pkg" / "index.js")
    _touch(tmp_path / "Projects" / "Phoenix" / "node_modules" / "left-pad" / "index.js")

    found = {p.resolve() for p in iter_files(tmp_path)}
    assert keep.resolve() in found
    assert all("node_modules" not in p.parts for p in found)


def test_iter_files_extra_skip_dirs_extends_denylist(tmp_path: Path):
    keep = _touch(tmp_path / "notes.txt")
    noise = _touch(tmp_path / "IgnoreMe" / "junk.log")

    default = {p.resolve() for p in iter_files(tmp_path)}
    assert keep.resolve() in default
    assert noise.resolve() in default

    extended = {
        p.resolve() for p in iter_files(tmp_path, extra_skip_dirs=["IgnoreMe"])
    }
    assert keep.resolve() in extended
    assert noise.resolve() not in extended


def test_opted_in_root_named_like_skip_still_walks_children(tmp_path: Path):
    """User-chosen root is not filtered by its own basename — only children are."""
    root = tmp_path / "node_modules"
    keep = _touch(root / "visible.txt")
    _touch(root / "nested" / "node_modules" / "pkg" / "index.js")

    found = {p.resolve() for p in iter_files(root)}
    assert keep.resolve() in found
    assert all(
        p.parts.count("node_modules") == 1 for p in found
    )  # only the opted-in root segment

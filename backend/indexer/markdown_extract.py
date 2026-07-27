"""Markdown extraction (#61 / Decision #007).

Indexes raw markdown so headings/lists remain searchable. Soft-fail only.
"""

from __future__ import annotations

from pathlib import Path

from indexer.extract import ExtractResult
from indexer.text_extract import extract_plain_text


def extract_md(path: Path | str) -> ExtractResult:
    """Read a ``.md`` / ``.markdown`` file into a single FTS segment (page=1)."""
    return extract_plain_text(path, parser="stdlib-md")

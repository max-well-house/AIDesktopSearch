"""Shared document extract contract + extension dispatch (#62 / Decision #007).

Thin registry for v0.6 — not a plugin platform. Soft-fail only at the
per-format extractors; dispatch returns error for unknown extensions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

ExtractStatus = Literal["ok", "empty", "error"]

# Formats with a registered extractor. Grow as #60 / #61 / #59 land.
CONTENT_EXTENSIONS: frozenset[str] = frozenset({"pdf"})


@dataclass
class ExtractResult:
    """Normalized extract output for any content format.

    ``pages`` is a list of (1-based segment, text). For PDFs, segment == page.
    For linear formats (TXT/MD/DOCX), use a single segment at page=1.
    """

    pages: list[tuple[int, str]] = field(default_factory=list)
    page_count: int = 0
    status: ExtractStatus = "ok"
    warnings: list[str] = field(default_factory=list)
    parser: str = "unknown"
    parser_version: str | None = None


def extension_of(path: Path | str) -> str:
    """Lowercase extension without the leading dot ('' if none)."""
    suffix = Path(path).suffix
    if not suffix or suffix == ".":
        return ""
    return suffix[1:].lower()


def extract_for_path(
    path: Path | str,
    *,
    max_seconds: float | None = None,
) -> ExtractResult:
    """
    Dispatch extract by file extension.

    Unknown / unregistered extensions → status=error (caller should not
    invoke this for non-CONTENT_EXTENSIONS paths).
    """
    ext = extension_of(path)
    if ext == "pdf":
        from indexer.pdf_extract import extract_pdf

        return extract_pdf(path, max_seconds=max_seconds)

    return ExtractResult(
        status="error",
        warnings=[f"no parser registered for extension {ext!r}"],
        parser="none",
    )

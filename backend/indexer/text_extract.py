"""Plain-text extraction shared by TXT (#60) and Markdown (#61).

Soft-fail only — never raise into the index worker for bad files.
Indexes raw text (markdown structure preserved as-written for FTS).
"""

from __future__ import annotations

from pathlib import Path

from indexer.extract import ExtractResult

MAX_TEXT_BYTES = 50 * 1024 * 1024  # 50 MiB — align with PDF cap
# Backward-compatible name.
MAX_TXT_BYTES = MAX_TEXT_BYTES

# Try in order; last entry may use replacement characters.
_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


def extract_plain_text(path: Path | str, *, parser: str) -> ExtractResult:
    """
    Read a text-like file into a single FTS segment (page=1).

    Encoding: utf-8-sig → utf-8 → cp1252 → latin-1 (replace). Soft-fails on
    missing/oversize/unreadable files. Content is not stripped to prose —
    headings/lists in Markdown stay in the indexed text.
    """
    resolved = Path(path)
    result = ExtractResult(parser=parser, page_count=1)

    try:
        size = resolved.stat().st_size
    except OSError as exc:
        result.status = "error"
        result.warnings.append(f"stat failed: {exc}")
        result.page_count = 0
        return result

    if size > MAX_TEXT_BYTES:
        result.status = "error"
        result.warnings.append(f"file exceeds {MAX_TEXT_BYTES} bytes; skipped extract")
        result.page_count = 0
        return result

    try:
        raw = resolved.read_bytes()
    except OSError as exc:
        result.status = "error"
        result.warnings.append(f"read failed: {exc}")
        result.page_count = 0
        return result

    if not raw:
        result.status = "empty"
        result.warnings.append("empty file")
        result.pages = []
        result.page_count = 0
        return result

    text: str | None = None
    used: str | None = None
    for enc in _ENCODINGS:
        try:
            if enc == "latin-1":
                text = raw.decode(enc, errors="replace")
                used = enc
                if "\ufffd" in text:
                    result.warnings.append(
                        "decoded with latin-1 using replacement characters"
                    )
                break
            text = raw.decode(enc)
            used = enc
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        result.status = "error"
        result.warnings.append("decode failed for all candidate encodings")
        result.page_count = 0
        return result

    # Normalize newlines for stable FTS; keep content otherwise intact.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if used and used not in ("utf-8", "utf-8-sig"):
        result.warnings.append(f"decoded as {used}")

    if not text.strip():
        result.status = "empty"
        result.warnings.append("no extractable text")
        result.pages = []
        result.page_count = 0
        return result

    result.pages = [(1, text)]
    result.page_count = 1
    result.status = "ok"
    return result


def extract_txt(path: Path | str) -> ExtractResult:
    """Read a ``.txt`` file (#60)."""
    return extract_plain_text(path, parser="stdlib-txt")

"""PDF text extraction via PyMuPDF (#54 / Decision #006).

Soft-fail only — never raise into the index worker for bad PDFs.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MiB
MAX_PDF_PAGES = 2000
# Soft wall clock budget per file (#58) — leave headroom for Ollama later.
MAX_PDF_EXTRACT_SECONDS = 30.0

PdfStatus = Literal["ok", "empty", "error"]


@dataclass
class PdfExtractResult:
    pages: list[tuple[int, str]] = field(default_factory=list)  # 1-based page, text
    page_count: int = 0
    status: PdfStatus = "ok"
    warnings: list[str] = field(default_factory=list)
    parser: str = "pymupdf"
    parser_version: str | None = None


def _pymupdf_version() -> str | None:
    try:
        import pymupdf

        return getattr(pymupdf, "version", None) and str(pymupdf.version[0])
    except Exception:  # noqa: BLE001
        return None


def extract_pdf(
    path: Path | str,
    *,
    max_seconds: float | None = None,
) -> PdfExtractResult:
    """
    Extract per-page text from a PDF.

    Caps: skip files larger than MAX_PDF_BYTES or with more than MAX_PDF_PAGES
    (status=error, warning set). Scanned/near-empty → status=empty.
    Soft-fails if extract exceeds max_seconds (default MAX_PDF_EXTRACT_SECONDS).
    """
    resolved = Path(path)
    version = _pymupdf_version()
    result = PdfExtractResult(parser_version=version)
    budget = MAX_PDF_EXTRACT_SECONDS if max_seconds is None else float(max_seconds)

    try:
        size = resolved.stat().st_size
    except OSError as exc:
        result.status = "error"
        result.warnings.append(f"stat failed: {exc}")
        return result

    if size > MAX_PDF_BYTES:
        result.status = "error"
        result.warnings.append(f"file exceeds {MAX_PDF_BYTES} bytes; skipped extract")
        return result

    try:
        import pymupdf
    except ImportError as exc:
        result.status = "error"
        result.warnings.append(f"pymupdf not installed: {exc}")
        return result

    try:
        doc = pymupdf.open(resolved)
    except Exception as exc:  # noqa: BLE001
        result.status = "error"
        result.warnings.append(f"open failed: {exc}")
        return result

    try:
        if getattr(doc, "needs_pass", False) or getattr(doc, "is_encrypted", False):
            # Some encrypted docs still open with empty user password; treat lock as soft fail.
            try:
                if doc.needs_pass and not doc.authenticate(""):
                    result.status = "error"
                    result.warnings.append("encrypted PDF; skipped extract")
                    return result
            except Exception:  # noqa: BLE001
                result.status = "error"
                result.warnings.append("encrypted PDF; skipped extract")
                return result

        page_count = int(doc.page_count)
        result.page_count = page_count
        if page_count > MAX_PDF_PAGES:
            result.status = "error"
            result.warnings.append(
                f"page_count {page_count} exceeds {MAX_PDF_PAGES}; skipped extract"
            )
            return result

        pages: list[tuple[int, str]] = []
        total_chars = 0
        started = time.monotonic()
        for i in range(page_count):
            if time.monotonic() - started >= budget:
                result.pages = pages
                result.status = "error"
                result.warnings.append(
                    f"extract exceeded {budget:g}s after {len(pages)} page(s); stopped early"
                )
                return result
            try:
                text = doc.load_page(i).get_text("text") or ""
            except Exception as exc:  # noqa: BLE001
                result.warnings.append(f"page {i + 1} extract failed: {exc}")
                text = ""
            pages.append((i + 1, text))
            total_chars += len(text.strip())

        result.pages = pages
        if total_chars == 0:
            result.status = "empty"
            result.warnings.append("no extractable text (scanned or empty)")
        else:
            result.status = "ok"
        return result
    except Exception as exc:  # noqa: BLE001
        result.status = "error"
        result.warnings.append(f"extract failed: {exc}")
        result.pages = []
        return result
    finally:
        try:
            doc.close()
        except Exception:  # noqa: BLE001
            pass

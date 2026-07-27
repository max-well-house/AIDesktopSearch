"""Split extracted page text into embeddable chunks (#66)."""

from __future__ import annotations

from dataclasses import dataclass

# Defaults sized for desktop meaning search (plan lock for v0.7).
CHUNK_SIZE = 640
CHUNK_OVERLAP = 80


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    page: int | None
    text: str


def chunk_text(
    text: str,
    *,
    page: int | None = None,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    start_index: int = 0,
) -> list[TextChunk]:
    """
    Character-window chunks with overlap.

    Empty / whitespace-only input → no chunks. Overlap is clamped below size.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    size = max(32, int(chunk_size))
    ov = max(0, min(int(overlap), size - 1))
    step = max(1, size - ov)

    out: list[TextChunk] = []
    idx = int(start_index)
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(start + size, length)
        piece = cleaned[start:end].strip()
        if piece:
            out.append(TextChunk(chunk_index=idx, page=page, text=piece))
            idx += 1
        if end >= length:
            break
        start += step
    return out


def chunk_pages(
    pages: list[tuple[int, str]],
    *,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[TextChunk]:
    """
    Page-aware chunking: each page is windowed separately; chunk_index is
    global across the file so replace_file_embeddings stays stable.
    """
    out: list[TextChunk] = []
    next_index = 0
    for page, text in pages:
        pieces = chunk_text(
            text,
            page=int(page),
            chunk_size=chunk_size,
            overlap=overlap,
            start_index=next_index,
        )
        out.extend(pieces)
        if pieces:
            next_index = pieces[-1].chunk_index + 1
    return out

"""Micro-benchmark for PDF sync (#58).

Creates a small temp corpus, cold-syncs PDFs into a temp SQLite DB, prints wall time.
Run from repo root:

  python scripts/bench_pdf_parse.py
  python scripts/bench_pdf_parse.py --files 20 --pages 5
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def _write_text_pdf(path: Path, pages: list[str]) -> None:
    import pymupdf

    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Bench cold PDF sync (#58)")
    parser.add_argument("--files", type=int, default=10, help="Number of PDFs")
    parser.add_argument("--pages", type=int, default=3, help="Pages per PDF")
    args = parser.parse_args()

    import os

    from db import init_db
    from indexer import ensure_root, replace_root_files
    from indexer.content import sync_pdfs_for_root

    with tempfile.TemporaryDirectory(
        prefix="aidesktop-pdf-bench-",
        ignore_cleanup_errors=True,
    ) as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "bench.db"
        os.environ["AIDESKTOP_DB"] = str(db_path)
        init_db(db_path)

        folder = tmp_path / "corpus"
        pdfs: list[Path] = []
        for i in range(args.files):
            path = folder / f"doc{i:03d}.pdf"
            _write_text_pdf(
                path,
                [f"bench file {i} page {p} searchable text" for p in range(args.pages)],
            )
            pdfs.append(path)

        root_id = ensure_root(folder)

        # Cold sync: wipe content path by using replace_root_files (includes sync).
        t0 = time.perf_counter()
        replace_root_files(root_id, pdfs)
        cold_s = time.perf_counter() - t0

        # Warm sync (mtime skip) — should be near-instant.
        t1 = time.perf_counter()
        sync_pdfs_for_root(root_id)
        warm_s = time.perf_counter() - t1

        print(f"files={args.files} pages_each={args.pages}")
        print(f"cold_sync_s={cold_s:.4f}")
        print(f"warm_skip_s={warm_s:.4f}")
        print(f"cold_per_file_s={cold_s / max(args.files, 1):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

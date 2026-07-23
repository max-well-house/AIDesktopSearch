#!/usr/bin/env python3
"""Generate a deterministic developer corpus for v0.3 filename indexing.

Default output is **outside the repo** (under the user Documents folder) so
indexer/search tests mirror real opt-in roots and avoid false confidence from
scanning the project tree.

Usage (from repo root):
  python tools/corpus/generate.py
  python tools/corpus/generate.py --seed 42 --clean
  python tools/corpus/generate.py --out D:\\Other\\Corpus --clean

Later milestones can extend this script; keep v0.3 stubs (fake extensions, no real PDFs).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_SEED = 42
MANIFEST_NAME = "manifest.json"
CORPUS_VERSION = 1
# Outside the repo on purpose — see tools/corpus/README.md
DEFAULT_CORPUS_DIRNAME = "MosAIq-TestCorpus"

# Filename search control set — milestone success: "Search Invoice finds invoice.pdf"
INVOICE_REL_PATHS = (
    "Documents/invoice.pdf",
    "Documents/Invoice-Acme.pdf",
    "Projects/Phoenix/phoenix-invoice-2024.pdf",
)

PHOENIX_REL_PATHS = (
    "Projects/Phoenix/README.md",
    "Projects/Phoenix/phoenix-budget.xlsx",
    "Projects/Phoenix/Meeting Notes.docx",
    "Projects/Phoenix/config.json",
    "Projects/Phoenix/architecture.png",
    "Projects/Phoenix/phoenix-invoice-2024.pdf",
)


@dataclass
class FileSpec:
    """One file to materialize under the corpus root."""

    rel_path: str
    content: bytes = b""
    tags: list[str] = field(default_factory=list)
    should_ignore: bool = False


def _default_out() -> Path:
    """Local machine path (not inside the git repo)."""
    documents = Path.home() / "Documents"
    if documents.is_dir():
        return documents / DEFAULT_CORPUS_DIRNAME
    return Path.home() / DEFAULT_CORPUS_DIRNAME


def _stub(label: str, body: str = "") -> bytes:
    text = f"STUB ({label}) — filename-index fixture only.\n"
    if body:
        text += body.rstrip() + "\n"
    return text.encode("utf-8")


def _build_specs(rng: random.Random) -> list[FileSpec]:
    specs: list[FileSpec] = []

    def add(
        rel: str,
        *,
        content: bytes | None = None,
        tags: list[str] | None = None,
        should_ignore: bool = False,
        empty: bool = False,
    ) -> None:
        data = b"" if empty else (content if content is not None else _stub(Path(rel).suffix or "file"))
        specs.append(
            FileSpec(
                rel_path=rel.replace("\\", "/"),
                content=data,
                tags=list(tags or []),
                should_ignore=should_ignore,
            )
        )

    # --- Documents (classic filename hits) ---
    add(
        "Documents/invoice.pdf",
        content=_stub("pdf", "control: invoice"),
        tags=["filename_hit:invoice", "control"],
    )
    add(
        "Documents/Invoice-Acme.pdf",
        content=_stub("pdf", "control: Invoice Acme"),
        tags=["filename_hit:invoice", "control"],
    )
    add("Documents/Resume.docx", content=_stub("docx"))
    add("Documents/Employee Handbook.pdf", content=_stub("pdf"))
    add("Documents/Meeting Notes.docx", content=_stub("docx"))
    add("Documents/Shopping List.txt", content=_stub("txt", "- milk\n- eggs"))
    add("Documents/TODO.md", content=_stub("md", "# TODO\n- index files"))
    add("Documents/Recipes.txt", content=_stub("txt"))

    # --- Projects / Phoenix (filename + later semantic stories) ---
    add(
        "Projects/Phoenix/README.md",
        content=_stub("md", "# Project Phoenix"),
        tags=["project:phoenix", "filename_hit:phoenix"],
    )
    add(
        "Projects/Phoenix/phoenix-budget.xlsx",
        content=_stub("xlsx", "phoenix budget"),
        tags=["project:phoenix", "filename_hit:phoenix", "filename_hit:budget"],
    )
    add(
        "Projects/Phoenix/Meeting Notes.docx",
        content=_stub("docx"),
        tags=["project:phoenix", "filename_hit:phoenix"],
    )
    add(
        "Projects/Phoenix/config.json",
        content=b'{"project":"Phoenix","env":"dev"}\n',
        tags=["project:phoenix", "filename_hit:phoenix"],
    )
    add(
        "Projects/Phoenix/architecture.png",
        content=_stub("png"),
        tags=["project:phoenix", "filename_hit:phoenix"],
    )
    add(
        "Projects/Phoenix/phoenix-invoice-2024.pdf",
        content=_stub("pdf", "phoenix invoice"),
        tags=["project:phoenix", "filename_hit:phoenix", "filename_hit:invoice", "control"],
    )

    add("Projects/Apollo/notes.txt", content=_stub("txt", "Apollo notes"))
    add("Projects/Apollo/README.md", content=_stub("md", "# Apollo"))
    add("Projects/Atlas/plan.md", content=_stub("md", "# Atlas"))
    add("Projects/Atlas/checklist.txt", content=_stub("txt"))

    # --- Code samples ---
    add("Code/Python/hello.py", content=b'print("hello")\n')
    add("Code/Python/utils.py", content=b"def noop():\n    pass\n")
    add("Code/React/App.tsx", content=b"export default function App() { return null }\n")
    add("Code/React/index.js", content=b'console.log("hi")\n')
    add("Code/TypeScript/types.ts", content=b"export type Id = string\n")
    add("Code/Rust/main.rs", content=b"fn main() {}\n")
    add("Code/CSharp/Program.cs", content=b"Console.WriteLine(\"hi\");\n")
    add("Code/Java/Main.java", content=b"class Main { public static void main(String[] a) {} }\n")

    # --- Misc typed folders ---
    add("Images/photo.png", content=_stub("png"))
    add("Images/diagram.jpg", content=_stub("jpg"))
    add("Music/track.mp3", content=_stub("mp3"))
    add("Videos/clip.mp4", content=_stub("mp4"))
    add("Archives/backup.zip", content=_stub("zip"))
    add("Logs/app.log", content=_stub("log", "INFO boot"))
    add("CSV/employees.csv", content=b"name,role\nJane Doe,Engineer\n")
    add("JSON/settings.json", content=b'{"theme":"dark"}\n')
    add("XML/data.xml", content=b"<root><item>1</item></root>\n")
    add("HTML/index.html", content=b"<html><body>corpus</body></html>\n")

    # --- Empty ---
    add("Empty/empty.txt", empty=True, tags=["empty"])
    add("Empty/empty.pdf", empty=True, tags=["empty"])
    add("Empty/empty.docx", empty=True, tags=["empty"])

    # --- Duplicates (same content, different names) ---
    dup_body = _stub("txt", "duplicate payload")
    add("Duplicates/duplicate.txt", content=dup_body, tags=["duplicate"])
    add("Duplicates/duplicate_copy.txt", content=dup_body, tags=["duplicate"])
    add("Duplicates/resume (copy).docx", content=_stub("docx"), tags=["duplicate"])

    # --- Unicode / awkward names ---
    add("Unicode/résumé.docx", content=_stub("docx"), tags=["unicode"])
    add("Unicode/こんにちは.txt", content=_stub("txt", "hello"), tags=["unicode"])
    add("Unicode/😀notes.md", content=_stub("md", "# notes"), tags=["unicode", "emoji"])
    add(
        "Unicode/really_really_really_long_filename_that_goes_on_and_on.txt",
        content=_stub("txt"),
        tags=["long_name"],
    )

    # --- Deep nesting ---
    add("Nested/a/b/c/d/e/deep-file.txt", content=_stub("txt", "deep"), tags=["deep"])

    # --- Ignore candidates (#45 hidden, #46 node_modules, denylist noise) ---
    add(
        ".hidden/secret.txt",
        content=_stub("txt", "hidden"),
        tags=["hidden"],
        should_ignore=True,
    )
    add(
        ".hidden/nested/cache.bin",
        content=_stub("bin"),
        tags=["hidden"],
        should_ignore=True,
    )
    add(
        "node_modules/some-pkg/index.js",
        content=b"module.exports = {}\n",
        tags=["node_modules"],
        should_ignore=True,
    )
    add(
        "node_modules/some-pkg/package.json",
        content=b'{"name":"some-pkg"}\n',
        tags=["node_modules"],
        should_ignore=True,
    )
    add(
        "Projects/Phoenix/node_modules/left-pad/index.js",
        content=b"module.exports = x => x\n",
        tags=["node_modules", "project:phoenix"],
        should_ignore=True,
    )
    add(
        ".git/config",
        content=b"[core]\n\trepositoryformatversion = 0\n",
        tags=["vcs"],
        should_ignore=True,
    )
    add(
        "IgnoreMe/noise.txt",
        content=_stub("txt", "denylist noise"),
        tags=["denylist"],
        should_ignore=True,
    )
    add(
        "IgnoreMe/junk.log",
        content=_stub("log"),
        tags=["denylist"],
        should_ignore=True,
    )

    # --- Seeded filler (extra variety; still deterministic) ---
    exts = [".txt", ".md", ".json", ".csv", ".log", ".py", ".js"]
    for i in range(12):
        ext = rng.choice(exts)
        name = f"filler_{i:02d}{ext}"
        add(
            f"Filler/{name}",
            content=_stub(ext.lstrip("."), f"filler {i}"),
            tags=["filler"],
        )

    # Stable order for identical manifests across platforms
    specs.sort(key=lambda s: s.rel_path.casefold())
    return specs


def _write_file(root: Path, spec: FileSpec) -> dict:
    path = root / spec.rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(spec.content)
    st = path.stat()
    return {
        "path": spec.rel_path,
        "name": path.name,
        "extension": path.suffix.lower(),
        "size": st.st_size,
        "tags": sorted(spec.tags),
        "should_ignore": spec.should_ignore,
    }


def _expected_search(files: list[dict]) -> dict[str, list[str]]:
    """Map lowercase query → relative paths whose names contain the query."""
    queries = ("invoice", "phoenix", "budget", "resume", "duplicate")
    out: dict[str, list[str]] = {}
    for q in queries:
        hits = sorted(
            f["path"]
            for f in files
            if q in f["name"].casefold() and not f["should_ignore"]
        )
        out[q] = hits
    return out


def generate(out_dir: Path, seed: int, clean: bool) -> dict:
    out_dir = out_dir.resolve()
    if clean and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    specs = _build_specs(rng)
    files = [_write_file(out_dir, spec) for spec in specs]

    ignore_count = sum(1 for f in files if f["should_ignore"])
    manifest = {
        "version": CORPUS_VERSION,
        "milestone": "v0.3.0",
        "purpose": "filename indexing / scan / ignore control set",
        "seed": seed,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(out_dir),
        "counts": {
            "total": len(files),
            "should_ignore": ignore_count,
            "should_index": len(files) - ignore_count,
        },
        "control": {
            "invoice_paths": list(INVOICE_REL_PATHS),
            "phoenix_paths": list(PHOENIX_REL_PATHS),
        },
        "expected_search": _expected_search(files),
        "files": files,
    }

    manifest_path = out_dir / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    # Manifest is metadata for tests — not part of the indexed file list.
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate a deterministic v0.3 test corpus for filename indexing.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=_default_out(),
        help=f"Output directory (default: {_default_out()})",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"RNG seed for deterministic filler (default: {DEFAULT_SEED})",
    )
    p.add_argument(
        "--clean",
        action="store_true",
        help="Delete the output directory before generating",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = generate(args.out, args.seed, args.clean)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    counts = manifest["counts"]
    print(f"Corpus written to: {manifest['root']}")
    print(
        f"Files: {counts['total']} "
        f"(index ~{counts['should_index']}, ignore ~{counts['should_ignore']})"
    )
    print(f"Manifest: {os.path.join(manifest['root'], MANIFEST_NAME)}")
    invoice_hits = manifest["expected_search"].get("invoice", [])
    print(f"expected_search['invoice']: {len(invoice_hits)} hit(s)")
    for rel in invoice_hits:
        print(f"  - {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

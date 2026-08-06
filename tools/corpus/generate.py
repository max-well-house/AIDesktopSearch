#!/usr/bin/env python3
"""Generate a deterministic developer corpus for classic / semantic / RAG eval.

Default output is **outside the repo** (under the user Documents folder) so
indexer/search tests mirror real opt-in roots and avoid false confidence from
scanning the project tree.

Usage (from repo root):
  python tools/corpus/generate.py
  python tools/corpus/generate.py --seed 42 --clean
  python tools/corpus/eval_search.py
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
CORPUS_VERSION = 2
# Outside the repo on purpose — see tools/corpus/README.md
DEFAULT_CORPUS_DIRNAME = "Meshen-TestCorpus"

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

# Distinctive phrases for content / semantic control queries (#140).
SHOPPING_BODY = """Shopping list for weekend groceries
- milk
- eggs
- sourdough bread
- unsalted butter
"""

RECIPES_BODY = """Family chili recipe
Use smoked chipotle peppers and black beans.
Simmer for two hours until thick.
"""

PHOENIX_README = """# Project Phoenix

Phoenix is an internal ops dashboard for warehouse telemetry.
Key modules: inventory sync, alert routing, and nightly reports.
Codename token for eval: aurora-warehouse-telemetry.
"""

VACATION_BODY = """Amalfi coast travel notes

We stayed near Positano and took the ferry to Capri.
Pack light linen and a good camera for the cliff paths.
Eval token: lemon-grove-terrace-sunset.
"""

TODO_BODY = """# TODO

- finish Phoenix dashboard wiring
- buy milk for the office fridge
- schedule chipotle chili night
"""

APOLLO_NOTES = """Apollo launch checklist
Verify thruster calibration and ground station handoff.
Eval token: lunar-relay-handshake.
"""


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


def _text(body: str) -> bytes:
    return (body.rstrip() + "\n").encode("utf-8")


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

    # --- Documents (classic filename + content hits) ---
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
    add(
        "Documents/Shopping List.txt",
        content=_text(SHOPPING_BODY),
        tags=["content:shopping", "control"],
    )
    add(
        "Documents/TODO.md",
        content=_text(TODO_BODY),
        tags=["content:todo", "control"],
    )
    add(
        "Documents/Recipes.txt",
        content=_text(RECIPES_BODY),
        tags=["content:recipes", "control"],
    )
    add(
        "Documents/vacation-italy.md",
        content=_text(VACATION_BODY),
        tags=["content:vacation", "control", "semantic"],
    )

    # --- Projects / Phoenix ---
    add(
        "Projects/Phoenix/README.md",
        content=_text(PHOENIX_README),
        tags=["project:phoenix", "filename_hit:phoenix", "content:phoenix", "control"],
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

    add(
        "Projects/Apollo/notes.txt",
        content=_text(APOLLO_NOTES),
        tags=["content:apollo", "control"],
    )
    add("Projects/Apollo/README.md", content=_text("# Apollo\n\nSibling project to Phoenix.\n"))
    add("Projects/Atlas/plan.md", content=_text("# Atlas\n\nMapping toolkit notes.\n"))
    add("Projects/Atlas/checklist.txt", content=_text("Atlas checklist\n- survey\n- publish\n"))

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

    # --- Duplicates ---
    dup_body = _text("duplicate payload for classic filename tests")
    add("Duplicates/duplicate.txt", content=dup_body, tags=["duplicate"])
    add("Duplicates/duplicate_copy.txt", content=dup_body, tags=["duplicate"])
    add("Duplicates/resume (copy).docx", content=_stub("docx"), tags=["duplicate"])

    # --- Unicode / awkward names ---
    add("Unicode/résumé.docx", content=_stub("docx"), tags=["unicode"])
    add("Unicode/こんにちは.txt", content=_text("hello from unicode fixture\n"), tags=["unicode"])
    add("Unicode/😀notes.md", content=_text("# notes\n\nemoji filename fixture\n"), tags=["unicode", "emoji"])
    add(
        "Unicode/really_really_really_long_filename_that_goes_on_and_on.txt",
        content=_text("long name fixture\n"),
        tags=["long_name"],
    )

    # --- Deep nesting ---
    add("Nested/a/b/c/d/e/deep-file.txt", content=_text("deep nesting fixture\n"), tags=["deep"])

    # --- Ignore candidates ---
    add(
        ".hidden/secret.txt",
        content=_text("hidden"),
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
        content=_text("denylist noise"),
        tags=["denylist"],
        should_ignore=True,
    )
    add(
        "IgnoreMe/junk.log",
        content=_stub("log"),
        tags=["denylist"],
        should_ignore=True,
    )

    # --- Seeded filler ---
    exts = [".txt", ".md", ".json", ".csv", ".log", ".py", ".js"]
    for i in range(12):
        ext = rng.choice(exts)
        name = f"filler_{i:02d}{ext}"
        add(
            f"Filler/{name}",
            content=_text(f"filler {i} — neutral noise document"),
            tags=["filler"],
        )

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


def _expectation(
    must_include: list[str],
    *,
    must_exclude: list[str] | None = None,
    top_k: int | None = None,
    mode: str = "classic",
    note: str | None = None,
) -> dict:
    entry: dict = {
        "must_include": list(must_include),
        "mode": mode,
    }
    if must_exclude:
        entry["must_exclude"] = list(must_exclude)
    if top_k is not None:
        entry["top_k"] = top_k
    if note:
        entry["note"] = note
    return entry


def _expected_search(files: list[dict]) -> dict[str, dict]:
    """Control queries → must_include (and optional exclude / mode)."""
    by_name: dict[str, list[str]] = {}
    for q in ("invoice", "phoenix", "budget", "resume", "duplicate"):
        by_name[q] = sorted(
            f["path"]
            for f in files
            if q in f["name"].casefold() and not f["should_ignore"]
        )

    return {
        "invoice": _expectation(by_name["invoice"], mode="classic", note="filename"),
        "phoenix": _expectation(by_name["phoenix"], mode="classic", note="filename"),
        "budget": _expectation(by_name["budget"], mode="classic", note="filename"),
        "resume": _expectation(by_name["resume"], mode="classic", note="filename"),
        "duplicate": _expectation(by_name["duplicate"], mode="classic", note="filename"),
        "sourdough": _expectation(
            ["Documents/Shopping List.txt"],
            mode="classic",
            note="classic FTS body",
        ),
        "chipotle peppers": _expectation(
            ["Documents/Recipes.txt"],
            mode="classic",
            note="classic FTS body",
        ),
        "aurora-warehouse-telemetry": _expectation(
            ["Projects/Phoenix/README.md"],
            mode="classic",
            note="classic FTS body",
        ),
        "Italian seaside trip notes": _expectation(
            ["Documents/vacation-italy.md"],
            mode="semantic",
            note="semantic meaning — needs embeddings",
        ),
        "warehouse dashboard project": _expectation(
            ["Projects/Phoenix/README.md"],
            mode="semantic",
            note="semantic meaning — needs embeddings",
        ),
    }


def _expected_rag() -> dict[str, dict]:
    """RAG control questions — asserted after #71/#72 (wave 3 / #140b)."""
    return {
        "What groceries are on the shopping list?": _expectation(
            ["Documents/Shopping List.txt"],
            mode="rag",
            note="RAG — deferred until citations ship",
        ),
        "What is Project Phoenix about?": _expectation(
            ["Projects/Phoenix/README.md"],
            mode="rag",
            note="RAG — deferred until citations ship",
        ),
        "Where did we stay on the Amalfi trip?": _expectation(
            ["Documents/vacation-italy.md"],
            mode="rag",
            note="RAG — deferred until citations ship",
        ),
    }


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
        "milestone": "v1.1.0",
        "purpose": "classic / semantic / RAG expected-hit control set",
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
        "expected_rag": _expected_rag(),
        "files": files,
    }

    manifest_path = out_dir / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate a deterministic v1.1 test corpus (content + expected hits).",
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
    invoice = manifest["expected_search"].get("invoice", {})
    invoice_hits = invoice.get("must_include", []) if isinstance(invoice, dict) else invoice
    print(f"expected_search['invoice'] must_include: {len(invoice_hits)} hit(s)")
    for rel in invoice_hits:
        print(f"  - {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

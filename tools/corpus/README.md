# Test corpus generator (v0.3)

Regenerable control set for **filename indexing**, folder scan, and ignore rules (`#40`–`#46`).

The **generator** lives in this repo. The **generated files** are written to your local machine **outside the project** so pointing MosAIq at the corpus behaves like a normal user folder — not like indexing the repo (which could hide bugs or create false positives).

Later milestones should add sibling issues to extend this tool (real PDFs, Office docs, semantic stories, etc.). This version only writes **stub** files with realistic names/extensions — not parseable Office/PDF binaries.

## Generate

From the repo root (Python 3; no extra deps):

```powershell
python tools/corpus/generate.py
```

Default output (Windows):

```text
%USERPROFILE%\Documents\MosAIq-TestCorpus
```

(macOS/Linux: `~/Documents/MosAIq-TestCorpus`, or `~/MosAIq-TestCorpus` if Documents is missing.)

Useful flags:

```powershell
python tools/corpus/generate.py --seed 42 --clean
python tools/corpus/generate.py --out D:\Other\MosAIq-TestCorpus --clean
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--out` | `Documents/MosAIq-TestCorpus` | Corpus root (**outside** the repo) |
| `--seed` | `42` | Deterministic filler; same seed → same tree |
| `--clean` | off | Delete `--out` before writing |

Generated files are **not** committed to GitHub. Only this tool is.

## Point the app at it

When folder pickers land (`#40`):

1. Generate the corpus (above).
2. Add **only** `Documents\MosAIq-TestCorpus` (absolute path) as an index root — do **not** add the AIDesktopSearch repo folder.
3. Do **not** treat `manifest.json` as a user document — it is test metadata in the corpus root. Prefer asserting against the `files` list in the manifest (or ignore `manifest.json` by name in tests).

## Manifest

`<out>/manifest.json` includes:

- `files[]` — relative `path`, `name`, `extension`, `size`, `tags`, `should_ignore`
- `expected_search` — e.g. query `invoice` → paths whose **names** contain `invoice` and are not ignore-tagged
- `control.invoice_paths` / `control.phoenix_paths` — fixed control lists for the milestone check (“Search Invoice finds invoice.pdf”)
- `counts` — total / should_index / should_ignore

Same `--seed` should produce the same relative paths and content (timestamps in `generated_at` will differ).

## What’s in the tree

- Nested projects (`Projects/Phoenix/…`), documents, code, images, archives, logs, CSV/JSON/XML/HTML
- Filename hits: `invoice.pdf`, `Invoice-Acme.pdf`, `phoenix-budget.xlsx`, …
- Edge cases: `Empty/`, `Duplicates/`, `Unicode/` (incl. emoji), deep `Nested/a/b/c/d/e/`
- Ignore candidates (`should_ignore: true` in the manifest):
  - Default scanner: `.hidden/`, `node_modules/` (any depth), `.git/` — see `backend/indexer/ignore.py`
  - Extensibility fixture: `IgnoreMe/` — not in defaults; pass `extra_skip_dirs=["IgnoreMe"]` (or add to `DEFAULT_SKIP_DIR_NAMES`) to exclude it

## Out of scope (this milestone)

Real PDF/DOCX/XLSX/PPTX bytes, OCR, emails, stress-size corpora, cross-format semantic story bodies. Add those when the matching product milestone needs them.

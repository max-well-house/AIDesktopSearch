# Test corpus generator

Regenerable **control set** for Meshen. The **generator** lives in this repo. **Generated files** are written **outside the project** (default: `%USERPROFILE%\Documents\Meshen-TestCorpus`) so indexing behaves like a normal user folder — never commit real personal docs or the generated tree to git.

## Policy (post-1.0)

Each major product milestone that needs new fixture *kinds* gets a **Corpus:** companion issue. Test data must keep up with the app.

| Milestone | Issue | Focus |
|-----------|-------|--------|
| v0.3 (done) | #113 | Filename stubs + ignore rules |
| v1.1 Local AI | #140 | Real text bodies + classic/semantic/RAG **expected hits** |
| v1.2 Images | #141 | OCR/description fixtures + expected hits |
| v1.3 Search UX | #142 | Snippets, fuzzy/zero-hit, excludes |
| v2.1 Actions | #143 | Move/rename reconcile |
| v3.1 AV | #144 | Speech phrases → files (after research go) |

### Expected-hit contract

`manifest.json` must support control queries where we assert:

- **must_include** — these relative paths must appear in results (the “these N files” bar)
- optional **must_exclude** / **top_k**

If a control search does not return the required files → **fail** (script or pytest). Same `--seed` → same tree and same expectations.

Implement / harden that contract in **#140**; later corpus issues extend it.

## Generate

From the repo root (Python 3; no extra deps for the v0.3 stub generator):

```powershell
python tools/corpus/generate.py
python tools/corpus/generate.py --seed 42 --clean
python tools/corpus/generate.py --out D:\Other\Meshen-TestCorpus --clean
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--out` | `Documents/Meshen-TestCorpus` | Corpus root (**outside** the repo) |
| `--seed` | `42` | Deterministic; same seed → same tree |
| `--clean` | off | Delete `--out` before writing |

## Point the app at it

1. Generate the corpus.
2. In Meshen Settings, add **only** that corpus folder as an index root — **not** the git repo.
3. Prefer asserting against `manifest.json` `files` / `expected_search` (treat `manifest.json` as test metadata, not a user doc).

## Manifest (today + direction)

Today (v0.3 / #113): `files[]`, `expected_search`, `control.invoice_paths` / `phoenix_paths`, `counts`.

Target (from #140): richer bodies + explicit **must_include** lists per control query for classic, semantic, and RAG, plus an automated check that fails on miss.

## What’s in the tree (v0.3 stubs)

- Nested projects, documents, code, images (stub), archives, logs, CSV/JSON/XML/HTML
- Filename hits: `invoice.pdf`, `Invoice-Acme.pdf`, …
- Ignore candidates: `.hidden/`, `node_modules/`, `.git/`, extensibility `IgnoreMe/`

Stub files may use realistic extensions **without** real Office/PDF binaries until #140+.

## Out of scope

- Personal Documents as the official fixture set
- Committing generated corpus bytes to GitHub

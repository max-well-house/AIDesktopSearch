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

`manifest.json` entries under `expected_search` / `expected_rag`:

```json
"sourdough": {
  "must_include": ["Documents/Shopping List.txt"],
  "mode": "classic",
  "must_exclude": [],
  "top_k": 10
}
```

- **must_include** — these relative paths must appear in results
- optional **must_exclude** / **top_k** / **mode** (`classic` | `semantic` | `rag`)

Same `--seed` → same tree and same expectations. Missing required files → eval **fails**.

## Generate

From the repo root (Python 3; stdlib only):

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

v1.1 bodies: real TXT/MD content with distinctive control phrases (shopping list, chipotle chili, Phoenix telemetry, Amalfi notes). PDF/DOCX remain filename stubs until a later corpus drop needs extractable binaries.

## Point the app at it

1. Generate the corpus.
2. In Meshen Settings, add **only** that corpus folder as an index root — **not** the git repo.
3. Wait for index (and embeddings if testing semantic).
4. Prefer asserting against `manifest.json` (treat it as test metadata, not a user doc).

## Eval

With the backend running and the corpus root indexed:

```powershell
python tools/corpus/eval_search.py
python tools/corpus/eval_search.py --modes classic
python tools/corpus/eval_search.py --include-rag
```

| Flag | Meaning |
|------|---------|
| `--manifest` | Path to `manifest.json` (default under Documents) |
| `--base-url` | API base (default `http://127.0.0.1:8000`) |
| `--modes` | Comma list: `classic`, `semantic` (default both) |
| `--include-rag` | Also run `expected_rag` (after #71/#72) |

Semantic rows are skipped when `semantic_query_ready` is false. RAG rows are skipped unless `--include-rag`.

## Manifest fields

- `version` — `2` for v1.1 content + structured expectations
- `expected_search` — classic + semantic control queries
- `expected_rag` — question → grounded files (assert after RAG ships)
- `control.invoice_paths` / `phoenix_paths` — filename control sets
- `files[]` — inventory with tags

## Out of scope

- Personal Documents as the official fixture set
- Committing generated corpus bytes to GitHub
- Image/OCR fixtures (#141), AV fixtures (#144)

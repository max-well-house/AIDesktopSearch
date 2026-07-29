# Decision #001

## Choice

Electron + React + Python + FastAPI

## Date

July 2026

## Why

- Leverages existing React skills
- Faster MVP development
- Strong AI ecosystem through Python
- Easier Cursor / pair-programming assistance
- Desktop shell is not the performance bottleneck for this product

## Tradeoffs accepted

- Higher baseline RAM usage than Tauri
- Larger app size
- Less native system integration

## Revisit when

- App becomes resource constrained in daily use on the primary machine
- A large user base exists and Electron memory is a proven problem
- Mobile becomes a real requirement

Do not plan a shell migration. Revisit only when forced by real usage.

## Status

Accepted
---

# Decision #002

## Choice

Hybrid search by default

## Date

July 2026

## Why

AI should enhance search, not replace it. Filename and keyword lookup must stay milliseconds-fast. The LLM should only run when the user needs synthesis or reasoning over document contents.

Routing order:

1. Classic filename / keyword search
2. Semantic search (when needed)
3. LLM + citations (when reasoning is needed)

The user should never pay the cost of AI when traditional methods are enough (example: find invoice.pdf).

## Tradeoffs accepted

- Need query routing / intent heuristics
- More moving parts than "always ask the LLM"

## Status

Accepted

## Implementation status (v0.7)

Hybrid live in `backend/search/routing.py` (#69): `mode=auto|hybrid` merges classic + semantic; filename-like queries stay classic-only; LLM still skipped (v0.8).

---

# Decision #003

## Choice

Operability bar: this machine first, with graceful degradation

## Date

July 2026

## Primary hardware profile

| Spec | Value |
|------|--------|
| CPU | Intel Core i5-14400F @ 2.50 GHz |
| System RAM | 16GB DDR5 |
| GPU | NVIDIA GeForce RTX 5060 Ti (8GB VRAM) |
| Storage | ~1.40 TB total, ~214 GB used |
| OS | Windows |

## Rules

1. Usable every day on the primary profile is non-negotiable.
2. Search must work without AI. If Ollama is missing or unhealthy, classic (and later semantic) search still works.
3. Prefer GPU inference for Ollama on this profile; support CPU-only and no-Ollama as degraded modes.
4. Corpus is opt-in folders — never whole-disk by default. Denylist noise (node_modules, hidden junk). Indexing is background and pauseable. **Whole-PC / whole-disk indexing is out of scope for defaults** (#40); the user explicitly chooses every root.
5. Cap retrieved chunks. No whole-PC-in-the-prompt.
6. Post-index latency: classic search feels instant; RAG under 1 minute on this machine, aiming for seconds with a VRAM-fitting quantized model.
7. Model size is configurable / machine-tiered. Defaults fit 16GB system RAM + 8GB VRAM beside OS + app + index.
8. Same architecture on weaker/stronger machines via settings ? not forks.
9. Never assume a specific GPU vendor or device name. Hardware detection is **capability-based** (`gpu.available`), not device-name-based (`if RTX 5060 Ti`). Prefer GPU on this profile; the same feature gates must work for AMD, Intel, CPU-only, and future hardware.

## Why

Avoid spending a year building something that demos well elsewhere but is unusable on the machine that matters most ? and still runs (degraded) elsewhere.

## Status

Accepted

---

# Decision #004

## Choice

Launcher-first UI with mosaic as idle brand (not permanent chrome)

## Date

July 2026

## Why

Meshen is a desktop search engine, not a chatbot. The launcher is the application; search is always the primary interaction. A subtle file-tile mosaic communicates the product metaphor on open ("your digital life as one connected mosaic") and gracefully fades when the user types so the workflow stays as fast and uncluttered as Raycast / Spotlight / PowerToys Run.

AI belongs inside search (and later results), not as a separate chat surface.

## Rules

1. Build production-quality components from the start ? no throwaway placeholder shells.
2. Keep the stable hierarchy: SearchBar ? MosaicCanvas (idle) / results slot ? Footer.
3. Mosaic exists permanently in the tree; visibility is an idle-state concern.
4. Theme tokens live in `frontend/src/theme.js` ? brand palette `#0D1117` / `#00E5A8` / `#22C55E` / `#06B6D4` / `#2563EB` / `#8CA3A0`.
5. Empty states use intentional guidance copy, not generic "No Results".
6. Brand mark is the mosaic M (`MosaIqMark` / favicon); keep window icon and favicon in sync.

## Status

Accepted

---

# Decision #005

## Choice

Filesystem watching via Python `watchdog` inside FastAPI (not Chokidar / Electron)

## Date

July 2026

## Why

- FastAPI is the brain: indexer, ignore rules, SQLite, and the change queue should share one owner (Decision #001 architecture).
- v0.3 scanner work (#40, #45, #46) already defines corpus roots and denylists in Python ? watching must reuse that path, not fork it into Node.
- Electron attach/spawn lifecycle (#96): watching can stay alive with the backend rather than dying when the shell quits in attach scenarios.
- Cross-platform (Windows now; macOS / Linux later) is a wash vs Chokidar ? both wrap FSEvents / inotify / ReadDirectoryChangesW. Preferring Mac or dual-boot Linux does **not** favor Chokidar; it favors keeping the product core in Python.
- Chokidar remains a documented alternate if Python watching proves painful; raw `fs.watch` and hand-rolled OS APIs are rejected; polling is startup / fallback only.

## Tradeoffs accepted

- Watcher status and control need FastAPI endpoints (UI still goes React ? Electron ? API).
- One more Python dependency; Linux large-tree `inotify` limits still apply (mitigate with opt-in roots + denylist, Decision #003).

## Rules for Phase 4

1. ~~Research only until v0.4~~ — implemented in `backend/indexer/watch.py` (#48–#52).
2. Pipeline: event → filter → queue → debounce/batch → index worker → SQLite (never one index job per raw event).
3. Start watching a root only after its initial index pass finishes; on cold start, reconcile then watch.
4. React never watches the filesystem.

## Revisit when

- `watchdog` cannot meet reliability or CPU goals on the primary machine after a real v0.4 spike
- A concrete product need requires the shell to own FS events (unlikely)

Full comparison: [research-filesystem-watchers.md](./research-filesystem-watchers.md).

## Status

Accepted

---

# Decision #006

## Choice

Primary PDF text extractor: **PyMuPDF** (`pymupdf`) in FastAPI; thin per-page extract contract for v0.5 (not a multi-format parser platform)

## Date

July 2026

## Why

- Phase 5 needs reliable text + **per-page** extract so classic search and page hints (#54–#57) work without Ollama (Decision #002 / #003).
- FastAPI already owns scan, ignore rules, watchdog, and SQLite (Decision #001 / #005) — PDF parsing belongs there, not in Electron.
- PyMuPDF is fast enough for background indexing on the primary machine and ships Windows wheels suitable for a local sidecar.
- A thin contract (path + per-page text + warnings / parser id) unblocks FTS without inventing chunkers, embeddings, or a `DocumentParser` registry before v0.6.
- OCR, tables, LangChain/Unstructured, and cloud parsers fight local-first scope or belong in later milestones (v0.7 / v0.9).

## Tradeoffs accepted

- PyMuPDF is **AGPL** (or commercial). Acceptable for this local open project; revisit if distribution / commercial packaging (#111) requires a permissive stack (pypdf alternate documented in research).
- Native binary dependency is heavier than pure-Python extractors.
- Table-heavy documents may be weaker until a specialty path (e.g. pdfplumber) is justified later.

## Rules for Phase 5

1. ~~Research only until #53 closes~~ — implemented extract/search in #54–#57.
2. All PDF parsing in Python / FastAPI — never Electron / PDF.js.
3. Prefer per-page text so #57 does not require a redesign.
4. Soft-fail scanned / empty / encrypted / corrupt PDFs (warning or empty content); do not block the index worker. OCR is not on the default path (v0.9).
5. No LangChain / Unstructured / Docling / MarkItDown as the core parser; no embeddings during parse (v0.7).
6. Do not build a multi-format `DocumentParser` registry until v0.6 needs it.
7. Content updates reuse scan / watch + `files.mtime` — extend the indexer; do not fork a second pipeline owner.

## Revisit when

- AGPL blocks a concrete packaging or distribution goal (#111)
- PyMuPDF cannot meet accuracy or CPU goals on the primary machine after a real #54 spike
- Product need for high-fidelity tables justifies a specialty secondary path

Full comparison: [research-pdf-libraries.md](./research-pdf-libraries.md).

## Status

Accepted

---

# Decision #007

## Choice

Thin multi-format extract registry in FastAPI (`ExtractResult` + `CONTENT_EXTENSIONS` + `extract_for_path`); reuse `file_content` / `file_pages_fts` without a schema bump. Linear formats store one FTS segment at `page=1`; launcher shows **Page N** only when `hit.extension === 'pdf'`.

## Date

July 2026

## Why

- Decision #006 deferred a multi-format registry until v0.6; Phase 6 (#62–#59) needs one dispatch path instead of more `extension == …` special cases.
- Schema already stores `parser` / `page` in a format-agnostic way — only Python dispatch was PDF-hardcoded.
- Fake “Page 1” captions on TXT/MD/DOCX would mislead; gating the UI on PDF keeps FTS simple.
- Still no chunkers, embeddings, or LangChain-class parsers (v0.7 / Decision #006 rules 4–5).

## Tradeoffs accepted

- One FTS segment for non-paged docs (no section-level hits until a later need).
- Registry is a plain extension map, not a plugin/entry-point system.

## Rules for Phase 6

1. All document parsing stays in Python / FastAPI — never Electron.
2. Soft-fail bad files; do not block the index worker.
3. Grow `CONTENT_EXTENSIONS` as #60 / #61 / #59 land; PDF remains on the shared contract.
4. Bulk sync (`sync_content_for_root`) must clear leftover content when extension is no longer eligible.
5. DOCX uses a separate permissive library (`python-docx`) — do not expand the AGPL surface casually.
6. No embeddings during parse (v0.7).

## Status

Accepted

---

# Decision #008

## Choice

Primary vector store: **sqlite-vec** (SQLite extension) in the FastAPI sidecar, same brain as `files` / FTS5. Chroma is not the default. LanceDB is the documented escape hatch if scale or packaging forces it.

## Date

July 2026

## Why

- Meshen already owns corpus state in SQLite; vectors should join to `files` / pages without a second source of truth.
- Opt-in personal corpora (Decision #003) fit exact k-NN; we do not need a server or cloud vector DB for v0.7.
- Hybrid search (#69) is simpler when classic FTS5 and vectors share one engine.
- Matches Decision #001 process model (FastAPI = brain; no extra daemon beside optional Ollama).
- Permissive license; avoids growing the AGPL surface.

## Tradeoffs accepted

- Native extension load on Windows (packaging detail for #67 / #111).
- Stable sqlite-vec is brute-force — revisit LanceDB (or ANN) if real corpora prove too slow.
- Younger dependency (pin versions; soft-fail if extension missing so classic search still works).

## Rules for Phase 7 store

1. Research only until #64 closes — implement persistence in #67.
2. Record `model_id` + dimension with stored vectors; do not mix embedding models without re-embed.
3. Semantic query must work from stored vectors when Ollama is down (Decision #003 / #63).
4. Missing sqlite-vec must not crash the API or classic search.
5. Do not adopt Chroma / Qdrant / cloud vector SaaS as the default path.

## Revisit when

- Exact k-NN is too slow on a real primary-machine corpus after opt-in growth
- Extension loading cannot be packaged reliably on a supported OS
- A concrete need for disk-ANN / versioned Lance datasets appears

Full comparison: [research-vector-databases.md](./research-vector-databases.md).

## Status

Accepted

---

# Decision #009

## Choice

Ship FastAPI with the Windows packaged app as a **staged runtime sidecar**: build-time venv + backend sources via electron-builder `extraResources` (not PyInstaller).

## Date

July 2026

## Why

- End users must not need a developer `.venv` (#111).
- Reuses #96 attach / owned spawn / `taskkill` tree cleanup with a different python path under `process.resourcesPath`.
- Native wheels (`pymupdf`, `sqlite-vec`) install into a normal venv; PyInstaller is a known footgun for those extensions and would burn calendar for little v1.0 benefit.
- Writable `index.db` stays under Electron `userData` via `AIDESKTOP_DB` when packaged.

## Tradeoffs accepted

- Larger portable artifact (full Windows venv + site-packages).
- Staging step on every `npm run package*` (`scripts/stage-backend-runtime.js` → `.packaging/`).
- Windows-first packaging only for v1.0.

## Rules

1. Unpackaged/dev still uses project `.venv` + repo `backend/`.
2. Packaged spawn: `resources/runtime/.../python` + `cwd=resources/backend`, no `--reload`.
3. Ollama remains optional and external (Decision #003).
4. Do not adopt PyInstaller unless staged-venv size or AV false positives force a freeze.

## Revisit when

- Portable size or antivirus false positives become a real support problem
- macOS/Linux packaging is required
- A freeze tool reliably bundles sqlite-vec + PyMuPDF on Windows

## Status

Accepted

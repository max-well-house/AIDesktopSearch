# Version 0.0.1

Foundation

Repo, board, docs, folder structure

Status: done (repo layout, GitHub board/milestones/issues, core docs) — milestone closed

---

# Version 0.0.2

Architecture Spike

Prove React → Electron → FastAPI → UI

Status: done (2026-07-14) — GitHub milestone closed 2026-07-15

- [x] Electron desktop window boots (`npm start` / `npm run dev`)
- [x] FastAPI status endpoint (`GET /` → status, version, timestamp, message)
- [x] Electron main process calls local FastAPI and surfaces result or connection error
- [x] React in the renderer (Vite) — Backend Connection Test via Electron IPC
- [x] Material UI (delivered in v0.1.0)

---

# Version 0.0.3

System Capability Detection

Backend reports what the machine can do; missing Ollama is OK (Decision #003)

Status: done (2026-07-14) — delivered via #95 + System Status UI (no separate GH milestone)

- [x] `GET /health` returns healthy API status + version
- [x] Detect Ollama available / unavailable / not_installed without crashing
- [x] Extensible `capabilities` schema (ollama, gpu via nvidia-smi, models)
- [x] React System Status screen shows API + Ollama
- [x] Capability Principle in vision; Decision #003 capability-based hardware rule

---

# Version 0.1.0

Desktop Shell

Native window, React UI, Material UI, packaging

Status: done (2026-07-15) — milestone closed

- [x] Electron window + React System Status (Material UI)
- [x] Hot reload (`npm run dev` — Vite + Electron)
- [x] Packaged Windows build (`npm run package` / `npm run package:portable` → `release/`)
- [x] Architecture docs match the running shell (`docs/architecture.md`)

---

# Version 0.1.1

Backend Lifecycle

Electron starts/stops FastAPI for one-command testing

Status: done (2026-07-22) — primary issue #96

- [x] Manage FastAPI process from Electron (#96)
- [x] README reflects one-command (or attach) workflow

Bridge before heavy v0.2.0 launcher work. (Python ships with the portable via Decision #009 / #111.)

---

# Version 0.2.0

Search Launcher

Status: done (2026-07-23) — GitHub milestone closed; #30–#37 complete

Global shortcut (prefer Alt+Space on Windows — #30), tray, Escape dismiss, Start with Windows, session window size, screenshots

Prerequisite: v0.1.1 (#96) strongly recommended

Product direction (Decision #004): launcher is the app; mosaic is idle brand; search-first, not chatbot. UI components are ship-quality foundations — not throwaway mocks.

Done:

- [x] Global shortcut (#30)
- [x] Search input / launcher foundation (#31)
- [x] Auto-focus (#32)
- [x] Escape dismiss + Alt+Space toggle (#33)
- [x] System tray (#34)
- [x] Start with Windows (#35)
- [x] Remember window size (#36) — session-only; Quit resets to default
- [x] Update screenshots (#37)

---

# Version 0.3.0

File Indexer

Opt-in folders (#40), SQLite filename search, hybrid routing stub (#98)

Done so far:
- Research filesystem watchers (#38) → Decision #005 + `docs/research-filesystem-watchers.md` (feeds v0.4; does not implement watching)
- SQLite foundation (#39) — `data/index.db`, `roots` + `files`
- Save metadata (#41) — `POST /index/scan` upsert/replace; Footer **Indexed** count + System Status scan
- Opt-in folder corpus (#40) — System Status add / rescan / remove roots; persists in SQLite; no whole-disk default
- Test corpus generator (#113)
- Classic filename search (#42) — `GET /search?q=` against `files.name` (IPC ready; launcher results UI → #43)
- Display results (#43) — launcher results slot lists filename hits; no-match / error states; open file → #44
- Open selected file (#44) — Enter/click → `shell.openPath`; missing path shows error; launcher hides on success

Done so far (continued):
- Ignore rules (#45 / #46) — hidden (dot) names + denylist (`node_modules`, …) in `indexer/ignore.py`; extensible via `DEFAULT_SKIP_DIR_NAMES` / `extra_skip_dirs`
- Hybrid query routing stub (#98) — `backend/search/routing.py`; `GET /search` reports `mode: classic` + skipped semantic/LLM hooks (no embeddings)
- Schema docs (#47) — `docs/schema.md` (`roots` / `files`, indexes, status fields)
- Footer Indexed date (#115) — `N files (locale date)` from `last_indexed_at`; omit date when unknown

**v0.3.0 complete** (open follow-ups move to later milestones).

---

# Version 0.4.0

Live File Watching

**Shipped (#48–#52):** Auto-update index via Python `watchdog` in FastAPI (Decision #005): event → filter → queue → debounce/batch → SQLite. Opt-in roots only; same ignore rules as scan. Pause/resume via `/index/watch/pause|resume`. Chokidar = alternate; startup reconcile = cold-start catch-up.

---

# Version 0.5.0

PDF Reading

Search inside PDFs

**Shipped (#53–#58):** Decision #006 + PyMuPDF extract → `file_content` / FTS5 → classic search merges filename + PDF body; launcher shows matching page. Open remains `shell.openPath` (no viewer page jump). #58: batched FTS writes, extract time budget, yield-between-PDFs, scan off event loop — see [research-pdf-libraries.md](./research-pdf-libraries.md) Performance.

---

# Version 0.6.0

Documents

DOCX / TXT / Markdown

**v0.6.0 complete** (#62 / #60 / #61 / #59):

- [x] Unified parser interface (#62) — `ExtractResult` + registry; PDF migrated; leftover clear; Page N UI gated to PDF
- [x] TXT parser (#60) — stdlib extract with encoding fallbacks; FTS segment page=1
- [x] Markdown parser (#61) — raw MD indexed (headings/lists preserved); `.md` / `.markdown`
- [x] DOCX parser (#59) — `python-docx` paragraphs + tables; soft-fail corrupt files

---

# Version 0.7.0

Semantic Search

Embeddings / meaning search (defaults fit 16GB + 8GB VRAM); GPU detection beyond stub (#112)

Done so far:
- Research embeddings (#63) → `docs/research-embeddings.md` (how embeddings fit Meshen; local vs cloud; generate ≠ query). Closed.
- Research vector DBs (#64) → Decision #008 + `docs/research-vector-databases.md` (sqlite-vec primary; LanceDB escape hatch; Chroma demoted).
- Install Ollama (#65) → local runner on the machine; `/health` + System Status detect/connect (probe from #95); README setup notes. Chat inference still #70; generate embeddings → #66.

Implementation order (dependency-correct):
1. **#67** Store embeddings — sqlite-vec load + chunk/vec schema + soft-fail + System Status verify. **Done.**
2. **#66** Generate embeddings — chunk + `nomic-embed-text` via Ollama + pauseable queue. **Done.**
3. **#68** Semantic search endpoint — query embed + k-NN + `run_semantic`. **Done.**
4. **#69** Hybrid search — classic-first escalate/merge (Decision #002). **Done.**
5. **#112** GPU capability detection — NVIDIA-first `nvidia-smi` on `/health` + System Status; capability gates via `gpu_preferred`. **Done.**
6. **#122** System Status diagnostics UX wrap — Status vs Advanced, opt-in **Start embedding** + done confirmation (no auto-enqueue on content sync). **Done.**

Defaults locked for this phase: sqlite-vec in same `index.db`; `nomic-embed-text`; page-aware PDF chunks; classic wins filename-like queries.

**v0.7.0 complete** (#63–#69, #112, #122). GitHub milestone closed 2026-07-28.

---

# Version 1.0.0

Daily Driver — storeable **classic + semantic** search

Polish and package so someone can download it and think “this works.” RAG and Images ship after as **v1.1 / v1.2**. A true **v2.0** waits for a later product era. Nice to Haves wait until after v1.0 **and** the 1.x AI/Images layers.

Must-ship (board):
- **#124** Product slim — auto-embed again; summary + contextual Pause; lab under Details — **done**
- **#80** Settings — corpus home; AppMark → Settings; prefs persist — **done**
- **#125** Show app version in Settings (support / About — not launcher chrome) — **done**
- **#86** Polish UI — concrete visual consistency (tones, radius, tokens, honest EmptyState) — **done**
- **#121** Hide native menu bar; theme window chrome / scrollbars — **done**
- **#120** Footer capability lights (Semantic live; AI off/yellow until v1.1) — **done**
- **#118** Per-root auto-watch toggle — **done**
- **#114** Privacy: stronger index.db wipe — **done**
- **#111** Ship Python/FastAPI with packaged release (+ coherent app icon) — **done**
- **#83** Keyboard navigation (close gaps) — **done**
- **#85** Performance (narrow: mosaic idle, embed load, startup) — **done**
- **#88–#90** Installation guide / User guide / Release notes — **done**

**v1.0.0 Daily Driver complete** (board must-ship closed 2026-07-28). Patches continue as **1.0.x** / **Up next**.

---

# Long-term eras (post-1.0)

**Milestone = one shippable release** (1.1, 1.2, …). **Era = product chapter** (1.x Find → 2.x Act → 3.x Expand → 4.x Connect). **2.0** starts Era 2 — not “when the 1.x backlog is empty.”

**Unplanned** (GitHub milestone): parking only for ideas not ready to milestone yet.

When closing a versioned milestone: update `docs/release-notes.md` and publish the GitHub Release (see `.cursor/rules/close-out-milestone.mdc`).

### Test corpus (keep fixtures in sync)

Regenerable corpus via `tools/corpus/` — **outside the repo**, never personal Documents as the official set. Each capability milestone that needs new fixture kinds has a **Corpus:** companion with **expected-hit** checks (query → these paths must appear, else fail). See [tools/corpus/README.md](../tools/corpus/README.md).

| Milestone | Corpus issue |
|-----------|----------------|
| v1.1 | #140 content + RAG/semantic/classic eval pack (**must-ship**) |
| v1.2 | #141 image/OCR fixtures |
| v1.3 | #142 Search UX fixtures |
| v2.1 | #143 move/rename reconcile fixtures |
| v3.1 | #144 AV speech fixtures (after research go) |

---

## Era 1.x — Find

Same product as 1.0: local files, search-first, AI optional.

### Up next (1.0.x polish)

**Shipped in 1.0.3:** #136 exe identity, #116 reset window, #128 supported types.  
**Shipped in 1.0.4:** #137 check for updates, #138 custom shortcut, #119 dismissible banners.  
**Queued for 1.0.5-class:** #145 Settings declutter, #146 first-run empty state (zero-roots Add folder CTA).


### Version 1.1.0 — Local AI

RAG answers + citations; guided Ollama setup (no terminal).

- **Must-ship:** #70, #71, #72, #133, #75, **#140** corpus eval pack
- **Stretch:** #73 conversation history, #74 better prompts, #99 chat model pick (after core RAG)

### Version 1.2.0 — Images

OCR / screenshot search. #76–#79 + **#141** corpus images.

### Version 1.3.0 — Search UX

#81 history + idle cards, #117 zero-hit recovery, #129 snippets, #132 preview research→build, #139 user excludes, **#142** corpus UX fixtures.

---

## Era 2.x — Act

Confirm-gated writes; index stays honest.

### Version 2.1.0 — Actions + reconcile

#104 confirm move/rename, #134 reconcile external moves, **#143** corpus fixtures.

### Version 2.2.0 — Suggest organize

#106 suggest folders → confirm → move + index update.

---

## Era 3.x — Expand

New kinds of understanding — **research-gated** (no fake implementation commitment).

### Version 3.1.0 — Audio/video search

#135 research → impl only after go; **#144** AV corpus fixtures after go.

### Version 3.2.0 — Connection map

#110 research → impl only after go.

---

## Era 4.x — Connect

### Version 4.1.0 — Opt-in sync

#103 settings/index sync; never silent file upload; off by default.

---

See also: [ideas.md](./ideas.md), [board audit 2026-07-15](./audit-2026-07-15.md)

# Roles

- Electron: dumb desktop shell (window, packaging, global launcher shortcut, system tray) and API gatekeeper (React never talks to FastAPI directly)
- React + Material UI: UI
- FastAPI: brain (index, search, AI)
- Ollama: separate process for local models (never inside Electron)
- Defaults sized for the primary profile (16GB system RAM + 8GB VRAM). Exact models chosen later against Decision #003.

# Frontend

## React

Why?

Already familiar

In repo now:

- Vite + React under `frontend/` (`src/main.jsx`, `src/App.jsx`, `src/theme.js`)
- System Status UI talks to FastAPI only via Electron IPC (`window.api.checkHealth`)
- Dev: `npm run dev` · built assets: `frontend/dist` via `npm run build` / `npm start`
- Package: `npm run package` / `npm run package:portable` → `release/`

---

## Electron

Why?

Cross platform

See Decision #001 (Electron + React + Python + FastAPI)

In repo now:

- Entry: `package.json` → `"main": "electron/main.js"`
- Shell: `electron/main.js`, `electron/preload.js`
- UI: `frontend/` (Vite + React + MUI) — System Status
- Scripts: `npm run dev` (Vite + Electron), `npm start` (build then Electron), `npm run package` / `npm run package:portable` (electron-builder → `release/`)
- Desktop → API call uses Electron `net.fetch` to local FastAPI `/health`; React only uses IPC (`window.api.checkHealth`)
- Packaging: electron-builder (`electron-builder.yml`) — Windows portable / unpacked dir; does not bundle Python
- FastAPI lifecycle: Electron attaches if healthy, else spawns from `.venv` and stops owned children on quit (#96)

---

## Material UI

Why?

Ready-made components for a consistent React UI

In repo now:

- `@mui/material` + Emotion + Roboto (`@fontsource/roboto`)
- Theme in `frontend/src/theme.js`; System Status uses MUI `Button` / `Typography` / `CssBaseline`

# Backend

## Python

Why?

AI ecosystem

---

## FastAPI

Why?

Simple local API for the desktop app backend

In repo now:

- `backend/main.py` with `GET /health` (and `GET /` shim) — `status`, `version`, `timestamp`, `capabilities`
- `backend/capabilities/` — Ollama + NVIDIA-first GPU probes + extensible schema (models.chat stub until #70)
- Deps: `backend/requirements.txt` (`fastapi`, `uvicorn`, `httpx`, `pydantic`)
- Dev server: `python -m uvicorn main:app --reload` from `backend/` (use project `.venv`)
- Default URL: `http://127.0.0.1:8000/health`

---

## SQLite

Why?

Simple

No server required

In repo now (#39):

- `backend/db/` — stdlib `sqlite3`; `init_db()` on FastAPI lifespan
- Default path: repo `data/index.db` (gitignored); override with `AIDESKTOP_DB`
- Schema foundation: `roots` + `files` (path, name, extension, size, mtime, indexed_at); `PRAGMA user_version = 1`
- `#41` — `POST /index/scan` upserts metadata + removes stale rows on rescan; `GET /index/status` feeds Footer **Indexed** count + System Status
- `#115` — Footer Indexed value appends short locale date from `last_indexed_at` when known
- `#40` — System Status lists corpus roots; add (pick + scan), rescan, remove (`DELETE /index/roots/{id}` + `VACUUM`); whole-PC indexing out of scope for defaults
- `#42` — `GET /search?q=` classic case-insensitive filename substring (Electron `api.search`)
- `#98` — classic-first routing stub (`backend/search/routing.py`); response includes `mode` + `stages_skipped`; semantic/LLM hooks unused
- `#43` — Launcher results slot lists hits from `api.search` (no-match / error)
- `#44` — Enter/click opens via Electron `shell.openPath` (`api.openPath`); missing path → error, launcher stays
- `#47` — Schema documented in `docs/schema.md`; forensic index wipe → #114 (v1.0)

---

## watchdog (v0.4.0)

Why?

Cross-platform filesystem events inside the Python indexer (Decision #005). Keeps ignore rules, queue, and SQLite updates in FastAPI — Electron stays the shell.

Installed via `backend/requirements.txt` (`watchdog`). Implementation: `backend/indexer/watch.py` (#48–#52). Chokidar is the documented alternate; polling is startup reconcile / fallback only.

Research: `docs/research-filesystem-watchers.md`.

---

## PyMuPDF (v0.5.0)

Why?

Fast per-page PDF text extract in the Python indexer (Decision #006). Classic content search and page hints (#54–#57) without Ollama.

Installed via `backend/requirements.txt` (`pymupdf`). Implementation: `backend/indexer/pdf_extract.py` behind shared `extract.py` registry (Decision #007 / #62); persist in `content.py`; FTS in SQLite (`file_pages_fts`). AGPL (or commercial) called out in research; acceptable for this local open project; revisit if packaging/distribution (#111) requires a permissive alternate (pypdf).

Research: `docs/research-pdf-libraries.md`.

---

## Stdlib text extract (v0.6.0)

Why?

Plain `.txt` and Markdown (`.md` / `.markdown`) body search without a new dependency (#60 / #61). Encoding tries utf-8-sig → utf-8 → cp1252 → latin-1 (replace). Markdown is indexed raw so headings/lists stay searchable.

Implementation: `backend/indexer/text_extract.py` + `markdown_extract.py` via `extract_for_path` (Decision #007).

---

## python-docx (v0.6.0)

Why?

Word `.docx` body search in the Python indexer (#59 / Decision #007). MIT license — keeps the AGPL surface limited to PyMuPDF.

Installed via `backend/requirements.txt` (`python-docx`). Implementation: `backend/indexer/docx_extract.py` (paragraphs + table cells → one FTS segment). Legacy `.doc` not supported.

---

## Ollama

Why?

Local models (embeddings in v0.7; chat/RAG in v0.8)

Separate process; prefer GPU on the primary machine. Never installed into the repo or parented under Electron.

Detected via `/health` (`available` / `unavailable` / `not_installed`). Missing Ollama never crashes the API. Install/docs for local dev: README **Optional: Ollama** (#65). Chat prompt wiring remains #70.

---

## Embeddings (v0.7)

Meaning search over chunk vectors. Classic FTS stays first (Decision #002). Local embed models preferred; cloud optional/explicit (Decision #003).

Research: `docs/research-embeddings.md` (#63). Generate/store/search → #66–#68; hybrid → #69.

---

## sqlite-vec

Why?

Local vector search inside the existing SQLite brain (Decision #008). Same process as FastAPI indexer; joins to `files` / FTS5 for hybrid (#69).

Package: `sqlite-vec` (pip). Loaded per connection in `backend/db/connection.py`; soft-fail if missing. Schema + store API: `backend/embeddings/` (#67). Default dim **768** (`nomic-embed-text`). System Status shows Vector store; **Verify vector store** smoke is under Diagnostics → Advanced (#122). Embedding generate is opt-in via **Start embedding** (no auto-enqueue on content sync).

Escape hatch: LanceDB if brute-force or packaging fails. Chroma demoted (was early placeholder only).

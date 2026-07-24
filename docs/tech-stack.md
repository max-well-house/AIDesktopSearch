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
- `backend/capabilities/` — Ollama probe + extensible schema (gpu/models stubs)
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
- `#40` — System Status lists corpus roots; add (pick + scan), rescan, remove (`DELETE /index/roots/{id}` + `VACUUM`); whole-PC indexing out of scope for defaults
- `#42` — `GET /search?q=` classic case-insensitive filename substring (Electron `api.search`)
- `#98` — classic-first routing stub (`backend/search/routing.py`); response includes `mode` + `stages_skipped`; semantic/LLM hooks unused
- `#43` — Launcher results slot lists hits from `api.search` (no-match / error)
- `#44` — Enter/click opens via Electron `shell.openPath` (`api.openPath`); missing path → error, launcher stays
- Full schema docs → #47; forensic index wipe → #114 (v1.0)

---

## watchdog (planned — v0.4.0)

Why?

Cross-platform filesystem events inside the Python indexer (Decision #005). Keeps ignore rules, queue, and SQLite updates in FastAPI — Electron stays the shell.

Not installed yet. Research: `docs/research-filesystem-watchers.md`. Chokidar is the documented alternate; polling is startup/fallback only.

---

## Ollama

Why?

Local models

Separate process; prefer GPU on the primary machine

Detected via `/health` (`available` / `unavailable` / `not_installed`). Missing Ollama never crashes the API.

---

## Chroma

Why?

Local vector store for embeddings / semantic search

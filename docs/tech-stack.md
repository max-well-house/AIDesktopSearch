# Roles

- Electron: dumb desktop shell (window, tray, shortcuts, packaging) and API gatekeeper (React never talks to FastAPI directly)
- React + Material UI: UI
- FastAPI: brain (index, search, AI)
- Ollama: separate process for local models (never inside Electron)
- Defaults sized for the primary profile (16GB system RAM + 8GB VRAM). Exact models chosen later against Decision #003.

# Frontend

## React

Why?

Already familiar

In repo now:

- Vite + React under `frontend/` (`src/main.jsx`, `src/App.jsx`)
- Backend Connection Test UI talks to FastAPI only via Electron IPC (`window.api.checkBackend`)
- Dev: `npm run dev` · built assets: `frontend/dist` via `npm run build` / `npm start`

---

## Electron

Why?

Cross platform

See Decision #001 (Electron + React + Python + FastAPI)

In repo now:

- Entry: `package.json` → `"main": "electron/main.js"`
- Shell: `electron/main.js`, `electron/preload.js`
- UI: `frontend/` (Vite + React) — Backend Connection Test
- Scripts: `npm run dev` (Vite + Electron), `npm start` (build then Electron)
- Desktop → API call uses Electron `net.fetch` to local FastAPI; React only uses IPC (`window.api.checkBackend`)

---

## Material UI

Why?

Ready-made components for a consistent React UI

Status: not installed yet (planned for shell / home screen work)

# Backend

## Python

Why?

AI ecosystem

---

## FastAPI

Why?

Simple local API for the desktop app backend

In repo now:

- `backend/main.py` with `GET /` status payload (`status`, `version`, `timestamp`, `message`)
- Dev server: `python -m uvicorn main:app --reload` from `backend/` (use project `.venv`)
- Default URL: `http://127.0.0.1:8000`

---

## SQLite

Why?

Simple

No server required

---

## Ollama

Why?

Local models

Separate process; prefer GPU on the primary machine

---

## Chroma

Why?

Local vector store for embeddings / semantic search

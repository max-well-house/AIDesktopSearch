# Roles

- Electron: dumb desktop shell (window, tray, shortcuts, packaging)
- React + Material UI: UI
- FastAPI: brain (index, search, AI)
- Ollama: separate process for local models (never inside Electron)
- Defaults sized for the primary profile (16GB system RAM + 8GB VRAM). Exact models chosen later against Decision #003.

# Frontend

## React

Why?

Already familiar

---

## Electron

Why?

Cross platform

See Decision #001 (Electron + React + Python + FastAPI)

In repo now:

- Entry: `package.json` → `"main": "frontend/main.js"`, script `npm start`
- Main / preload / renderer spike under `frontend/`
- Desktop → API call uses Electron `net.fetch` to local FastAPI (avoids renderer CORS for this spike)

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

- `backend/main.py` with `GET /` hello
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

# AI Desktop Search

Local-first desktop search that finds your files by meaning and keyword.

See [vision.md](./docs/vision.md) for the one-page product vision, [architecture.md](./docs/architecture.md) for the architecture design, [decisions.md](./docs/decisions.md) for the decisions I made and why, [ideas.md](./docs/ideas.md) for the future implementation ideas, [roadmap.md](./docs/roadmap.md) for the project roadmap, [tech-stack.md](./docs/tech-stack.md) for the tech stack used in this project, and [audit-2026-07-15.md](./docs/audit-2026-07-15.md) for the latest board/milestone audit.

## Layout

```
docs/        Project documentation
electron/    Electron shell (main, preload) — gatekeeper to FastAPI
frontend/    React + Material UI (Vite)
backend/     FastAPI app
data/        Local data (gitignored when real indexes land)
tests/       Tests
release/     Packaged builds (gitignored; from npm run package*)
```

## Prerequisites

- Python 3.x
- Node.js + npm

## First-time setup (once)

From the repo root in PowerShell:

```powershell
# Python env + FastAPI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# Node deps (Electron, Vite, React, MUI, electron-builder)
npm install
```

## Spin up to test (every time)

You need **two terminals**. FastAPI and Electron are separate processes until Electron manages the backend (#96).

Endpoint framework (every API call follows this — React never hits FastAPI directly):

```
React → Electron (IPC) → FastAPI → Electron → React
```

### Terminal 1 — backend

```powershell
cd .
.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn main:app --reload
```

Leave this running. You should see uvicorn listening on `http://127.0.0.1:8000`.

Quick sanity check in a browser: open http://127.0.0.1:8000/health — you should get JSON with `status`, `version`, `timestamp`, and `capabilities`. API docs: http://127.0.0.1:8000/docs

### Terminal 2 — desktop UI

```powershell
cd .
npm run dev
```

That starts Vite and then opens the Electron window (hot reload).

### What to click

1. In the window, click **Check System Status**.
2. With the backend up → **Backend: Online**, plus Ollama status (Available / Unavailable / Not installed).
3. Stop Terminal 1 (`Ctrl+C`), click **Check System Status** again → **Unable to reach backend**.

### Other commands

| Command | What it does |
|---------|----------------|
| `npm run dev` | Vite + Electron (hot reload; preferred while developing) |
| `npm start` | Build React to `frontend/dist`, then open Electron against that build |
| `npm run package` | Build React, then write an unpacked app under `release/win-unpacked/` |
| `npm run package:portable` | Same, plus a double-clickable Windows portable `.exe` in `release/` |

Stop dev processes with `Ctrl+C` in their terminals.

### Packaged app

After `npm run package:portable`, launch:

- `release\AI Desktop Search 1.0.0.exe`, or
- `release\win-unpacked\AI Desktop Search.exe`

The window opens with the React UI. FastAPI is still started separately (Terminal 1) for System Status to show Online.

## How Electron talks to FastAPI

```
React (Check System Status)
  → preload.js (IPC: window.api.checkHealth)
  → electron/main.js (net.fetch)
  → http://127.0.0.1:8000/health
  → IPC result back to React
```

- `electron/main.js` — Electron main process; creates the window; calls FastAPI
- `electron/preload.js` — safe bridge (`window.api.checkHealth`)
- `frontend/` — React + Material UI System Status screen
- `electron-builder.yml` — packaging config

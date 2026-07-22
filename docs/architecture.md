# Architecture

```
                 User
                  |
            Electron App
                  |
        --------------------
        |                  |
     React UI          Node Main
     (MUI + Vite)      (gatekeeper)
        |                  |
        --------------------
                  |
              FastAPI
                  |
      ------------------------
      |          |           |
  Indexer    Search       AI Engine
      |          |           |
  SQLite    Vector DB    Ollama
      |
  Filesystem
```

Electron is a dumb shell (window, packaging, global launcher shortcut; tray later) and the **API gatekeeper**.
FastAPI is the brain (indexing, search, AI).
Ollama is a separate process — never parented directly under Electron.

---

## Process model (v0.1.1 Backend Lifecycle)

The app is **three cooperating processes** (plus optional Ollama):

| Process | How it starts | Role |
|---------|---------------|------|
| Electron main | `npm run dev` / `npm start` / packaged `.exe` | Window, IPC, `net.fetch`, FastAPI lifecycle |
| React renderer | Vite (dev) or `frontend/dist` (start / package) | System Status UI (Material UI) |
| FastAPI (uvicorn) | Electron attaches if healthy, else spawns from `.venv` | `GET /health` + future API |
| Ollama (optional) | User / OS; never required | Local models when present |

```
One command:  Electron → (attach or spawn uvicorn :8000) → React UI
Optional:     Ollama → :11434
```

Lifecycle rules (`electron/backendProcess.js`):

- Probe `/health` on ready. Healthy → **attach** (do not kill on quit).
- Otherwise spawn `python -m uvicorn main:app` from repo `.venv` (**no `--reload`** for owned children).
- On quit, stop **only** a process Electron spawned (Windows: `taskkill /t`).
- Missing `.venv` or spawn failure: open the UI anyway; System Status stays offline. Never require Ollama.

Override project root with `AIDESKTOP_ROOT` when the working directory is unusual.

### Dev vs packaged

| Mode | Command | UI source | Backend |
|------|---------|-----------|---------|
| Hot reload | `npm run dev` | Vite at `http://127.0.0.1:5173` | Electron attach or spawn |
| Built in-repo | `npm start` | `frontend/dist` via `loadFile` | Electron attach or spawn |
| Packaged | `npm run package` / `package:portable` | asar `frontend/dist` | Attach, or spawn if `.venv` visible; Python not bundled |

Packaging: electron-builder → `release/win-unpacked/` or portable `release/<productName> <version>.exe`. Config: `electron-builder.config.js` (reads `app.config.json`). Does not bundle Python (#111).

---

## Endpoint framework (v0.0.2+)

All UI → backend traffic uses this round-trip. Only the FastAPI path and payload change later.

```
React
  ↓
Electron (IPC in, net.fetch out)
  ↓
FastAPI
  ↓
Electron (IPC result)
  ↓
React
```

React never calls FastAPI with `fetch`.

---

## Current path (v0.1.0)

Proven path: **React → Electron → FastAPI → Electron → React** (System Status / capabilities).

```
User clicks Check System Status
 |
React UI (frontend/ — MUI ThemeProvider + System Status)
 |
preload.js  (contextBridge → window.api.checkHealth)
 |
main.js     (ipcMain + net.fetch, cache: no-store)
 |
http://127.0.0.1:8000/health   FastAPI GET /health
 |
{ status, version, timestamp, capabilities: { ollama, gpu, models } }
 |
IPC result → React System Status UI
```

| Piece | Location | Role |
|-------|----------|------|
| Main process | `electron/main.js` | Window lifecycle; HTTP to local FastAPI `/health`; loads Vite URL (dev) or `frontend/dist` (built/packaged) |
| Preload | `electron/preload.js` | Exposes `checkHealth` to the renderer |
| Renderer UI | `frontend/src/` (Vite + React + MUI) | System Status (API + Ollama) |
| Theme | `frontend/src/theme.js` | MUI theme |
| Backend | `backend/main.py` + `backend/capabilities/` | Health + capability detection |
| Packaging | `electron-builder.yml` | Windows portable / unpacked dir under `release/` |

### `GET /health` contract

Always **200** when the API process is up. Ollama missing/stopped never becomes a 5xx.

```json
{
  "status": "healthy",
  "version": "0.0.3",
  "timestamp": "...Z",
  "capabilities": {
    "ollama": {
      "available": false,
      "status": "not_installed",
      "version": null,
      "base_url": "http://127.0.0.1:11434"
    },
    "gpu": { "available": null, "name": null, "note": "..." },
    "models": { "chat": false, "embedding": false }
  }
}
```

Ollama `status`: `available` | `unavailable` | `not_installed`. Clients ignore unknown capability keys so future fields (`storage`, etc.) do not break older UIs.

`GET /` returns the same payload (compatibility shim).

Rules for this wiring:

- Use the local URL only (`http://127.0.0.1:8000/health`).
- Call FastAPI from main (or preload), not by loading `main.py` as a file.
- Connection failures must be visible in the UI (debuggable).
- Renderer must not `fetch` FastAPI directly.

---

## High-level component layout

```
AIDesktopSearch/
  electron/           Main + preload (gatekeeper)
  frontend/           Vite + React + MUI
    src/App.jsx       System Status screen
    dist/             Production UI assets
  backend/            FastAPI app
    main.py           /health (+ / shim)
    capabilities/     Ollama probe, schema stubs
  release/            Packaged builds (gitignored)
  docs/               Vision, architecture, decisions, roadmap
```

**In place (v0.1.1):** native window, React + Material UI, hot reload, electron-builder packaging, System Status over IPC, Electron-managed FastAPI lifecycle (#96).

**Global shortcut (#30):** `Alt+Space` shows/focuses the main window from anywhere (`Control+Shift+Space` if registration fails). Registered in `electron/main.js` via Electron `globalShortcut`; cleared on `will-quit`. Remapping belongs with Settings (#80).

**Later:** tray / Escape (v0.2.0), indexer / search (v0.3.0+), GPU detection beyond stub (#112), freeze Python into installer (#111).

---

## Query routing (Decision #002)

Planned product behavior — not implemented in the UI yet. Still the target design.

```
Question comes in
       |
       v
Can classic search answer this?
       |
   Yes --------> Return instantly
       |
       No
       v
Use semantic search
       |
Need reasoning?
       |
       v
Ask LLM (with citations)
```

---

## Operability modes (Decision #003)

Still accurate. `/health` already reports Ollama so the UI can degrade; search modes arrive with the indexer.

| Mode | When | Capabilities |
|------|------|----------------|
| Classic only | Ollama unavailable / RAM tight / AI off | Filename + keyword search |
| Classic + semantic | Vectors ready | Meaning search without LLM |
| Full RAG | Ollama healthy + user asks | Answers with citations |

Degrade cleanly. Never crash because AI is missing.

---

## Primary hardware profile

| Spec | Value |
|------|--------|
| CPU | Intel Core i5-14400F @ 2.50 GHz |
| System RAM | 16GB DDR5 |
| GPU | NVIDIA GeForce RTX 5060 Ti (8GB VRAM) |
| Storage | ~1.40 TB total, ~214 GB used |
| OS | Windows |

- System RAM budget: OS + Electron + FastAPI + index working set
- VRAM budget: local models via Ollama (prefer GPU on this profile)
- Weaker machines: classic/semantic; smaller or no local LLM
- Stronger machines: larger models via settings, same architecture

See Decision #003.

---

## Frontend

Electron (shell + gatekeeper — window, IPC, packaging, Alt+Space launcher shortcut; tray later)

React + Material UI (System Status via Vite + IPC)

## Backend

Python

FastAPI (`GET /health` capability endpoint live; Electron attaches or spawns from `.venv`)

SQLite (planned)

Ollama (optional; detected via `/health`, never required for classic path)

Chroma (planned)

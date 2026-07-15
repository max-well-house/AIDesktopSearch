# Architecture

```
                 User
                  |
            Electron App
                  |
        --------------------
        |                  |
     React UI          Node Main
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

Electron is a dumb shell (window, tray, shortcuts, packaging) and the **API gatekeeper**.
FastAPI is the brain (indexing, search, AI).
Ollama is a separate process — never parented directly under Electron.

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

## Current path (v0.0.3)

Proven path: **React → Electron → FastAPI → Electron → React** (System Status / capabilities).

```
User clicks Check System Status
 |
React UI (frontend/)
 |
preload.js  (contextBridge → window.api.checkHealth)
 |
main.js     (ipcMain + net.fetch)
 |
http://127.0.0.1:8000/health   FastAPI GET /health
 |
{ status, version, timestamp, capabilities: { ollama, gpu, models } }
 |
IPC result → React System Status UI
```

| Piece | Location | Role |
|-------|----------|------|
| Main process | `electron/main.js` | Window lifecycle; HTTP call to local FastAPI `/health` |
| Preload | `electron/preload.js` | Exposes `checkHealth` to the renderer |
| Renderer UI | `frontend/` (Vite + React) | System Status (API + Ollama) |
| Backend | `backend/main.py` + `backend/capabilities/` | Health + capability detection |

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

## Query routing (Decision #002)

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

Electron (shell + gatekeeper — in place)

React (System Status via Vite + IPC)

Material UI (planned for Desktop Shell)

## Backend

Python

FastAPI (`GET /health` capability endpoint live)

SQLite (planned)

Ollama (optional; detected via `/health`, never required for classic path)

Chroma (planned)

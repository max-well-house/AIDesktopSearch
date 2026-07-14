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

Electron is a dumb shell (window, tray, shortcuts, packaging).
FastAPI is the brain (indexing, search, AI).
Ollama is a separate process — never parented directly under Electron.

---

## Current spike (v0.0.2 progress)

Proven path today: **Electron → FastAPI hello → UI** (React still next).

```
User
 |
Electron window (index.html + renderer.js)
 |
preload.js  (contextBridge → window.api.getHello)
 |
main.js     (ipcMain + net.fetch)
 |
http://127.0.0.1:8000/   FastAPI GET /
 |
{"message": "Hello World"}
```

| Piece | Location | Role |
|-------|----------|------|
| Main process | `frontend/main.js` | Window lifecycle; HTTP call to local FastAPI |
| Preload | `frontend/preload.js` | Exposes a minimal API to the renderer |
| Renderer UI | `frontend/index.html`, `frontend/renderer.js` | Shows hello JSON or a connection error |
| Backend | `backend/main.py` | FastAPI app with `GET /` hello |

Rules for this wiring:

- Use the local URL only (`http://127.0.0.1:8000/`).
- Call FastAPI from main (or preload), not by loading `main.py` as a file.
- Connection failures must be visible in the UI (debuggable).

Still open for the full v0.0.2 spike: React in the renderer, Material UI, optional Ollama health check.

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

Electron (shell — in place for hello spike)

React (planned; not wired yet)

Material UI (planned)

## Backend

Python

FastAPI (hello endpoint live)

SQLite (planned)

Ollama (optional; not required for hello)

Chroma (planned)

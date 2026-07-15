# Notes

Scratchpad for decisions, open questions, and research. Prefer short dated entries.

## 2026-07-14
Goal:
Setup project folders, github repo, and project board

What I learned:
how much goes into planning and prepping

Problem:
i mnot usually great at this

Solution:
use the help of agents to help me understand what to do, where to do it, and why to do it

Next:
Launch the app (Milestone v0.1)

## 2026-07-14 — Stack lock

Locked Electron + React + Python/FastAPI (Decision #001).
Locked hybrid search (Decision #002) and operability bar for this PC first (Decision #003: i5-14400F, 16GB DDR5, RTX 5060 Ti 8GB).
Next: Architecture Spike (v0.0.2) then Desktop Shell (v0.1).

## 2026-07-14 — Architecture spike (Electron ↔ FastAPI)

Goal:
Prove the desktop shell can call the local FastAPI hello endpoint and show the result.

What I did:
- `npm init` + Electron (`frontend/main.js` entry, `npm start`)
- Kept FastAPI hello in `backend/main.py`
- Wired main → preload → renderer so the UI shows hello JSON or a connection error

What I learned:
Loading `backend/main.py` via `loadFile` does not call the API — it just opens the source file. The API must be requested over HTTP at `http://127.0.0.1:8000/`. Calling from the Electron main process (`net.fetch`) keeps CORS out of the way for this spike.

Problem:
Early scaffold mixed “show a page” with “talk to the backend.”

Solution:
`index.html` + `renderer.js` for UI; `preload.js` bridge; `main.js` owns the FastAPI request and surfaces errors.

Next:
Finish v0.0.2 leftovers (React + MUI in the renderer; Ollama optional), then Desktop Shell (v0.1).

## 2026-07-14 — React ↔ Electron ↔ FastAPI pipeline

Goal:
Prove the lasting endpoint framework with a Backend Connection Test UI.

What I did:
- Split `electron/` (main + preload) from `frontend/` (Vite + React)
- Enriched FastAPI `GET /` with status / version / timestamp / message
- Wired React → `window.api.checkBackend` → Electron `net.fetch` → FastAPI → UI
- `npm run dev` runs Vite + Electron together

What I learned:
The spike is not “can React call HTTP?” — it is proving React never talks to FastAPI directly so later endpoints reuse the same Electron gatekeeper.

Next:
Material UI + optional Ollama health (#95), then Desktop Shell (v0.1).
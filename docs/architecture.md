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

Electron is a dumb shell (window, packaging, global launcher shortcut, system tray) and the **API gatekeeper**.
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
| Backend | `backend/main.py` + `backend/capabilities/` + `backend/db/` | Health + capability detection; SQLite init (`data/index.db`) |
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
    "gpu": {
      "available": true,
      "name": "NVIDIA GeForce …",
      "note": "GPU preferred for Ollama"
    },
    "models": { "chat": false, "embedding": false }
  }
}
```

Ollama `status`: `available` | `unavailable` | `not_installed`. Clients ignore unknown capability keys so future fields (`storage`, etc.) do not break older UIs.

GPU (`#112`): NVIDIA-first via `nvidia-smi`. `available` is `true` (GPU found), `false` (tool ran, no GPU), or `null` (tool missing / unknown vendor). Optional `name` is display-only — feature gates use `gpu_preferred()` / `available is True` only (Decision #003 rule 9).

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
    main.py           /health (+ / shim); lifespan inits SQLite
    capabilities/     Ollama probe, schema stubs
    db/               SQLite connection + files/roots schema (#39)
  data/               Local index DB (gitignored) — `index.db`
  release/            Packaged builds (gitignored)
  docs/               Vision, architecture, decisions, roadmap
```

**In place (v0.2.0):** native window, React + Material UI launcher (mosaic idle), hot reload, electron-builder packaging, System Status over IPC, Electron-managed FastAPI lifecycle (#96), Alt+Space toggle, Escape dismiss, system tray, Start with Windows, session window size.

**Global shortcut (#30 / #33):** `Alt+Space` toggles the launcher (`Control+Shift+Space` if registration fails). When focused → hide and **keep** the query (pause). Otherwise → show/focus. Registered in `electron/main.js` via Electron `globalShortcut`; cleared on `will-quit`. Remapping belongs with Settings (#80).

**Escape (#33):** Dismiss — main sends `launcher:dismiss`; renderer `flushSync`-clears/remounts the search box, paints one frame, then hides. Next Alt+Space shows at opacity 0, scrubs again, then opacity 1 so reopen never flashes stale text. App stays running in the tray.

**System tray (#34 / #35):** `Tray` in `electron/main.js` with `resources/icon.ico`. Left-click toggles show/hide (keep query). Context menu: Show, **Start with Windows** (checkbox via `app.setLoginItemSettings` / `openAsHidden`), Quit. Window close (X) hides to tray; only Quit (or `app.quit`) exits and stops the backend. Login / `--hidden` starts with the window hidden (tray + Alt+Space ready). Works best when packaged; unpackaged registers the Electron binary with the app path and `--hidden`.

**Window size (#36):** Session-only. Esc / Alt+Space / tray hide keep the live window size; tray Quit (cold start) resets to 720×480 (min 480×360). No cross-session file.

**Later:** freeze Python into installer (#111). GPU detection shipped (#112).

---

## Live file watching (v0.4.0 — Decision #005)

Implemented in `backend/indexer/watch.py` (Python `watchdog` inside FastAPI).

```
Filesystem (opt-in roots only)
       │
       v
FastAPI + watchdog
  filter (denylist / hidden / temp; refuse paths outside root)
  → queue → debounce / batch
  → index worker → SQLite
       │
       v
Electron (IPC gatekeeper) → React (System Status / progress only)
```

- **Primary:** Python `watchdog` in the same process as the indexer (#48–#52).
- **Security boundary:** same as scan — only user-opted-in `roots`; metadata only (path/name/size/mtime); symlink escape blocked via `resolve()` + `relative_to(root)`.
- **Lifecycle:** startup reconciles each root (full rescan) then watches; `POST /index/scan` starts/refreshes a watch; `DELETE /index/roots/{id}` stops it first.
- **Control:** `POST /index/watch/pause` / `resume`; `GET /index/status` includes `watching`, `watched_roots`, `queue_depth`, `watch_paused`.
- **Alternate / fallback:** Chokidar documented only; polling = startup reconcile (and if native watching fails later).
- React never watches the filesystem.

Details: [research-filesystem-watchers.md](./research-filesystem-watchers.md).

---

## Query routing (Decision #002)

Live in `backend/search/routing.py` (#69 / audit follow-ups 2026-07-28):

- `*.ext` (and empty) → classic-only when classic hits; **empty classic escalates** to semantic when vectors + query embedder are ready.
- Short concepts / phrases (`pokemon`, `fire dragon`, NL intent words) → **hybrid** (classic first, semantic fills; cosine distance ≤ `SEMANTIC_MAX_DISTANCE`, always keep nearest).
- Soft-fail to classic if Ollama cannot embed the query. LLM still v0.8.

```
Question comes in
       |
       v
Classic filename / keyword
       |
hits + filename-like? --> Return classic
       |
else (or classic empty)
       v
Semantic (query embed + k-NN) when ready
       |
Need reasoning? (later)
       v
Ask LLM (with citations)
```

---

## Operability modes (Decision #003)

Still accurate. `/health` already reports Ollama so the UI can degrade; search modes arrive with the indexer.

| Mode | When | Capabilities |
|------|------|----------------|
| Classic only | Ollama unavailable / RAM tight / AI off / no vectors | Filename + keyword search |
| Classic + semantic | Vectors ready **and** query embedder (Ollama + `nomic-embed-text`) up | Meaning search without chat LLM; soft-falls to classic if query embed fails |
| Full RAG | Ollama healthy + user asks | Answers with citations |

Degrade cleanly. Never crash because AI is missing. Embeddings notes: [research-embeddings.md](./research-embeddings.md) (#63). Vector store: [research-vector-databases.md](./research-vector-databases.md) (#64 / Decision #008 — sqlite-vec).

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

Electron (shell + gatekeeper — window, IPC, packaging, Alt+Space toggle, Escape dismiss, system tray)

React + Material UI (System Status via Vite + IPC)

## Backend

Python

FastAPI (`GET /health` capability endpoint live; Electron attaches or spawns from `.venv`)

SQLite (`data/index.db` — created on API startup; #39). Table/field reference: [schema.md](./schema.md) (#47). `PRAGMA user_version = 2` adds PDF `file_content` + `file_pages_fts` (#55).


Opt-in corpus roots only (#40): the user adds folders via System Status; `DELETE /index/roots/{id}` removes a root, cascades file rows, and runs `VACUUM` (light reclaim of free pages — not forensic wipe; see #114). Whole-PC / whole-disk indexing is out of scope for defaults (Decision #003).

Launcher Footer **Indexed** shows file count plus a short locale date from `last_indexed_at` when known (#115); no separate footer chip.

### Scan ignore rules (#45 / #46)

`backend/indexer/ignore.py` is the single source of truth for the scanner and the live watcher (Decision #005).

| Rule | Default behavior |
|------|------------------|
| Hidden names | Dot-prefixed dirs and files (`.git`, `.hidden`, `.env`, …) are skipped. Does not yet check Windows `FILE_ATTRIBUTE_HIDDEN`. |
| Denylist dirs | Exact basenames in `DEFAULT_SKIP_DIR_NAMES` are pruned at any depth — includes `node_modules`, VCS (`.git`/…), venvs, caches, `dist`/`build`, `.next`/`.turbo`. |
| Extending | Add names to `DEFAULT_SKIP_DIR_NAMES`, or pass `extra_skip_dirs=` into `iter_files` for one scan. |
| Opted-in root | The user-chosen root itself is never skipped by name; only its children are filtered. |

`watchdog` (v0.4.0 live watching; Decision #005 — `backend/indexer/watch.py`)

### Document content (v0.5.0 PDF — Decision #006; v0.6.0 registry — Decision #007)

**Shipped PDF (#54–#58); unified dispatch (#62):**

```
File → extract_for_path (by extension) → file_content + file_pages_fts → classic search hit (+ page for PDF)
```

| Piece | Location |
|-------|----------|
| Shared contract / registry | `backend/indexer/extract.py` (`ExtractResult`, `CONTENT_EXTENSIONS`, `extract_for_path`) |
| PDF extract | `backend/indexer/pdf_extract.py` (size / page / time caps) |
| Persist / re-parse | `backend/indexer/content.py` (`sync_file_content`, `sync_content_for_root`, leftover clear; hooked from `metadata`) |
| Search merge | `backend/indexer/search.py` — filename LIKE ∪ FTS5; one hit per file |
| UI | `ResultsList` shows `Page N` only for PDF hits with `hit.page`; Enter still `shell.openPath` (no viewer page jump) |

- Soft-fail empty / scanned / encrypted / corrupt / oversize / timed-out; OCR deferred to v0.9.
- Re-parse when `files.mtime` ≠ `file_content.mtime_at_parse`.
- Scan runs content work in a worker thread so `/health` and `/search` stay responsive during index (#58).
- **v0.6.0 shipped:** TXT / Markdown / DOCX (#60 / #61 / #59) on the shared registry (Decision #007).
- **Still later:** embeddings/chunking (v0.7), background pauseable content queue / Ollama-aware throttling.

Details: [research-pdf-libraries.md](./research-pdf-libraries.md). Schema: [schema.md](./schema.md).

Ollama (optional; detected via `/health`, never required for classic path). Local install/docs: README **Optional: Ollama** (#65). Chat wiring → #70.

sqlite-vec (planned — Decision #008; store in #67)

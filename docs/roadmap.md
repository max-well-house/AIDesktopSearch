# Version 0.0.1

Foundation

Repo, board, docs, folder structure

Status: done (repo layout, GitHub board/milestones/issues, core docs) — milestone closed

---

# Version 0.0.2

Architecture Spike

Prove React → Electron → FastAPI → UI

Status: done (2026-07-14) — GitHub milestone closed 2026-07-15

- [x] Electron desktop window boots (`npm start` / `npm run dev`)
- [x] FastAPI status endpoint (`GET /` → status, version, timestamp, message)
- [x] Electron main process calls local FastAPI and surfaces result or connection error
- [x] React in the renderer (Vite) — Backend Connection Test via Electron IPC
- [x] Material UI (delivered in v0.1.0)

---

# Version 0.0.3

System Capability Detection

Backend reports what the machine can do; missing Ollama is OK (Decision #003)

Status: done (2026-07-14) — delivered via #95 + System Status UI (no separate GH milestone)

- [x] `GET /health` returns healthy API status + version
- [x] Detect Ollama available / unavailable / not_installed without crashing
- [x] Extensible `capabilities` schema (ollama, gpu stub, models stub)
- [x] React System Status screen shows API + Ollama
- [x] Capability Principle in vision; Decision #003 capability-based hardware rule

---

# Version 0.1.0

Desktop Shell

Native window, React UI, Material UI, packaging

Status: done (2026-07-15) — milestone closed

- [x] Electron window + React System Status (Material UI)
- [x] Hot reload (`npm run dev` — Vite + Electron)
- [x] Packaged Windows build (`npm run package` / `npm run package:portable` → `release/`)
- [x] Architecture docs match the running shell (`docs/architecture.md`)

---

# Version 0.1.1

Backend Lifecycle

Electron starts/stops FastAPI for one-command testing

Status: done (2026-07-22) — primary issue #96

- [x] Manage FastAPI process from Electron (#96)
- [x] README reflects one-command (or attach) workflow

Bridge before heavy v0.2.0 launcher work. (Freezing Python into the installer is later — #111.)

---

# Version 0.2.0

Search Launcher

Status: done (2026-07-23) — GitHub milestone closed; #30–#37 complete

Global shortcut (prefer Alt+Space on Windows — #30), tray, Escape dismiss, Start with Windows, session window size, screenshots

Prerequisite: v0.1.1 (#96) strongly recommended

Product direction (Decision #004): launcher is the app; mosaic is idle brand; search-first, not chatbot. UI components are ship-quality foundations — not throwaway mocks.

Done:

- [x] Global shortcut (#30)
- [x] Search input / launcher foundation (#31)
- [x] Auto-focus (#32)
- [x] Escape dismiss + Alt+Space toggle (#33)
- [x] System tray (#34)
- [x] Start with Windows (#35)
- [x] Remember window size (#36) — session-only; Quit resets to default
- [x] Update screenshots (#37)

---

# Version 0.3.0

File Indexer

Opt-in folders (#40), SQLite filename search, hybrid routing stub (#98)

Done so far:
- Research filesystem watchers (#38) → Decision #005 + `docs/research-filesystem-watchers.md` (feeds v0.4; does not implement watching)
- SQLite foundation (#39) — `data/index.db`, `roots` + `files`
- Save metadata (#41) — `POST /index/scan` upsert/replace; Footer **Indexed** count + System Status scan
- Test corpus generator (#113)

Still open: #40 folder UX, #42–#46 search/results/ignores, #47 schema docs, #98 hybrid stub

---

# Version 0.4.0

Live File Watching

Auto-update index via Python `watchdog` in FastAPI (Decision #005): event → queue → debounce/batch → SQLite. Chokidar = alternate; polling = startup/fallback.

---

# Version 0.5.0

PDF Reading

Search inside PDFs

---

# Version 0.6.0

Documents

DOCX / TXT / Markdown

---

# Version 0.7.0

Semantic Search

Embeddings / meaning search (defaults fit 16GB + 8GB VRAM); GPU detection beyond stub (#112)

---

# Version 0.8.0

Local AI

RAG answers + citations (GPU-preferred; AI optional if Ollama down)

---

# Version 0.9.0

Images

OCR / screenshot search

---

# Version 1.0.0

Daily Driver

Settings, polish, guides; ship Python with packaged release (#111)

---

See also: [board audit 2026-07-15](./audit-2026-07-15.md)

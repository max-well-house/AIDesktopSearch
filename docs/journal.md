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
Early scaffold mixed "show a page" with "talk to the backend."

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
The spike is not "can React call HTTP?" — it is proving React never talks to FastAPI directly so later endpoints reuse the same Electron gatekeeper.

Next:
v0.0.3 System Capability Detection, then Desktop Shell (v0.1).

## 2026-07-14 — System Capability Detection (v0.0.3)

Goal:
Report what the machine can do without crashing when Ollama is missing.

What I did:
- `GET /health` with extensible `capabilities` (ollama probe, gpu/models stubs)
- Electron IPC → `/health`; React System Status UI
- Capability Principle in vision; Decision #003 capability-based GPU rule

Next:
Manual verification matrix, then Desktop Shell (v0.1) + Material UI.

## 2026-07-15 — Desktop Shell (v0.1.0)

Goal:
Land a real desktop shell: React + MUI window, hot reload, packaged build, docs in sync.

What I did:
- Material UI System Status screen; `npm run dev` Vite + Electron hot reload
- electron-builder packaging (`npm run package` / `package:portable` → `release/`)
- Updated `docs/architecture.md` (and README / tech-stack / roadmap) to match the process model

What I learned:
Packaging the shell is separate from shipping Python. Freezing FastAPI into the `.exe` is heavier than spawning the repo `.venv` later (#96).

Next:
#96 — Electron starts/stops FastAPI for one-command testing; then v0.2.0 Search Launcher (shortcut, tray, Escape).

## 2026-07-15 — Board audit (pre-forward)

Goal:
Clean milestones/issues after Desktop Shell so the next work is obvious.

What I did:
- Closed finished milestones v0.0.1 and v0.0.2; created **v0.1.1 Backend Lifecycle** for #96
- Closed #97 as duplicate of #40; cross-linked #98↔#69, #65↔#95/#70, shortcut note on #30
- Added gap issues #111 (ship Python with package) and #112 (GPU detection beyond stub)
- Wrote `docs/audit-2026-07-15.md`; synced roadmap, ideas, learning notes

## 2026-07-22 — Backend lifecycle (#96)

Goal:
One-command testing: Electron attaches to or spawns FastAPI; stops only what it owns.

What I did:
- Added `electron/backendProcess.js` (probe → attach / spawn from `.venv` / tree-kill stop)
- Wired `ensureBackend` before `createWindow` and `stopBackend` on `before-quit`
- Updated README + architecture process model for one-command / attach workflow

What I learned:
Owned children should not use uvicorn `--reload` on Windows — the reloader process tree is easy to orphan. Attach mode keeps a manual `--reload` terminal safe.

Next:
Close v0.1.1 on the board when verified; start v0.2.0 Search Launcher (shortcut, tray, Escape).

## 2026-07-22 � Launcher foundation (#31) + brand

Goal:
Ship the permanent search-launcher UI foundation and a rename-ready product identity.

What I did:
- Built launcher shell: SearchBar, MosaicCanvas (idle), EmptyState, Footer; mosaic fades when typing
- Brand palette + mosaic-M mark; dark `#0D1117` desktop `.ico`; `app.config.json` as single source for name/company/version
- Closed #31 search input (auto-focus included in SearchBar)

What I learned:
Windows shortcuts need a real multi-size `.ico` with a dark plate � light/white icon plates look cheap on the desktop. Product display names should not be hardcoded once packaging and UI both need them.

Next:
#32 autofocus issue (likely already satisfied � verify/close), #33 Escape, #34 tray; then real search wiring.

## 2026-07-23 — Search Launcher milestone (v0.2.0)

Goal:
Finish Phase 2 Search Launcher: shortcut, dismiss/toggle, tray, startup, polish — close the milestone.

What I did:
- Closed #32 (autofocus already in SearchBar from #31)
- #33 Escape dismiss (clear + hide) + Alt+Space toggle (keep query); scrub-on-reopen so no stale-text flash
- #34 System tray (Show / Quit; X hides; tray click toggles by visibility)
- #35 Start with Windows tray checkbox (`setLoginItemSettings`; unpackaged shows as Electron in Startup)
- #36 Window size session-only (keep while hidden; Quit → default 720×480)
- #37 Launcher screenshots in README + `docs/screenshots/`
- Closed GitHub milestone **v0.2.0 - Search Launcher** (8/8 issues)

What I learned:
- Tray click steals focus before the handler runs — toggle must use visibility, not `isFocused()`
- Windows `getLoginItemSettings` needs the same `path`/`args` as set, or the menu checkmark lies
- Packaged desktop shortcuts go stale; rebuild after shell UX lands or Esc/Alt+Space look "broken"

Next:
v0.3.0 File Indexer — opt-in folders (#40), SQLite filename search, hybrid routing stub (#98). Rebuild portable exe when daily-driving the shortcut.

## 2026-07-23 — Filesystem watcher research (#38)

Goal:
Decide how Phase 4 should detect file changes without implementing watching yet.

What I did:
- Compared watchdog, Chokidar, fs.watch, polling, and raw OS APIs
- Chose Python `watchdog` in FastAPI (Decision #005); Chokidar as alternate; polling as startup/fallback
- Documented event pipeline (queue → debounce → batch → SQLite) and Phase 4 requirements in `docs/research-filesystem-watchers.md`
- Closed #38

What I learned:
Mac/Linux later does not favor Chokidar — both libraries wrap the same native APIs. Architecture ownership (brain vs shell) matters more than the npm-vs-pip brand.

Next:
v0.3.0 implementation — SQLite (#39), scan folders (#40), filename index/search; leave live watching for v0.4.

## 2026-07-23 ? End of day (v0.3 kickoff)

Goal:
Start File Indexer after closing Search Launcher; lock watcher research; get metadata into SQLite with a visible confidence cue.

What I did:
- Closed **v0.2.0 Search Launcher** earlier today (#30?#37)
- #38 Watcher research ? Decision #005 (`watchdog` in FastAPI); docs in `research-filesystem-watchers.md`
- #39 SQLite init on API startup (`data/index.db`, `roots` + `files`)
- #113 Test corpus generator (fixtures outside the repo)
- #41 Save metadata ? scan upsert/replace, Footer **Indexed: N files**, System Status Browse/Scan (user-verified)

What I learned:
- Milestone framing matters: watcher research lives in v0.3 but product goal is still filename search; live watching is v0.4
- A durable Footer stub (`Indexed`) beats a throwaway debug screen for ?did the step work??

Next:
1. #40 ? proper opt-in folder add/remove UX (scan API already exists)
2. #42 ? filename search against SQLite
3. #47 ? document schema; tighten #45/#46 ignores as needed

## 2026-07-23 — End of day (v0.3 kickoff)

Goal:
Start File Indexer after closing Search Launcher; lock watcher research; get metadata into SQLite with a visible confidence cue.

What I did:
- Closed **v0.2.0 Search Launcher** earlier today (#30–#37)
- #38 Watcher research → Decision #005 (`watchdog` in FastAPI); docs in `research-filesystem-watchers.md`
- #39 SQLite init on API startup (`data/index.db`, `roots` + `files`)
- #113 Test corpus generator (fixtures outside the repo)
- #41 Save metadata — scan upsert/replace, Footer **Indexed: N files**, System Status Browse/Scan (user-verified)

What I learned:
- Milestone framing matters: watcher research lives in v0.3 but product goal is still filename search; live watching is v0.4
- A durable Footer stub (`Indexed`) beats a throwaway debug screen for "did the step work?"

Next:
1. #40 — proper opt-in folder add/remove UX (scan API already exists)
2. #42 — filename search against SQLite
3. #47 — document schema; tighten #45/#46 ignores as needed

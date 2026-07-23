# Learning Notes

Short dated notes on concepts and skills picked up during the project.

## Template

### MM/DD/YYYY — Topic

What I learned:

Why it matters:


### 07/14/2026

What I learned: How to create a repo, basic file structure, setting up a board with milestones, labels, columns, and issues. 

Why it matters: Helping me start this project organized, and set up for success.

### 07/14/2026 — Shell vs brain

What I learned: Electron vs Tauri is not the make-or-break choice for an AI desktop search app. System RAM, GPU VRAM, hybrid search routing, and opt-in indexing matter more for daily usability on a 16GB machine.

Why it matters: Keeps us from rewriting shells later instead of shipping a tool Max can actually run.

### 07/14/2026 — Electron main / preload / renderer

What I learned: Electron has three layers that matter for talking to FastAPI. The main process owns the window and can `net.fetch` localhost. Preload uses `contextBridge` to expose a tiny safe API. The renderer only displays results — it should not get Node/filesystem access. Also: `loadFile` on a `.py` file is not an API call; uvicorn must be running and you hit `http://127.0.0.1:8000/`.

Why it matters: This is the pattern we reuse with React in `frontend/` — same main/preload bridge; React only renders and invokes IPC, never talks to FastAPI directly.

### 07/14/2026 — React through Electron only

What I learned: For the architecture spike, “does React work?” is the wrong test. The right test is React → Electron → FastAPI → Electron → React. A renderer `fetch` to localhost would skip the gatekeeper we need for search / query / ask-ai later.

Why it matters: One IPC shape (`checkHealth` today) stays stable while FastAPI endpoints change.

### 07/14/2026 — System capability detection

What I learned: The app should ask "what can I do right now?" instead of assuming Ollama/GPU/models exist. `/health` always means "API is up"; Ollama missing is a capability signal (`not_installed` / `unavailable`), not a crash.

Why it matters: Classic search can ship without AI. The UI and API stay useful on every machine.

### 07/15/2026 — Packaging vs backend lifecycle

What I learned: electron-builder can ship a double-clickable Electron + React app without bundling Python. Freezing FastAPI into the installer is a separate, heavier problem from spawning the project `.venv` from Electron.

Why it matters: We can close the Desktop Shell milestone with a real packaged UI, then add FastAPI start/stop (#96) for one-command testing before Search Launcher work.

### 07/15/2026 — Board audit vs duplicate issues

What I learned: Early planning created parallel issues for the same product rule (e.g. opt-in folders as both #40 and #97) and left finished milestones open. A short audit pass — close empty milestones, fold duplicates, park carry-overs on a bridge milestone (v0.1.1), link nice-to-haves from `ideas.md` — makes "what next" obvious without deleting roadmap ambition.

Why it matters: Stops thrashing on Phase 3 noise and keeps #96 from floating without a home after leaving v0.1.0.

### 07/22/2026 — Owned uvicorn without --reload

What I learned: When Electron spawns FastAPI, skip uvicorn `--reload`. The reloader parent + worker child makes Windows cleanup (`taskkill /t` or otherwise) brittle. Attach-if-healthy still lets a manual `--reload` terminal keep running across Electron restarts.

Why it matters: One-command `npm run dev` can start and stop the backend without orphaning zombies, while debug workflows stay flexible.



Question: How should the app detect hardware acceleration without baking in "RTX 5060 Ti"?

Approaches to evaluate later:

1. **nvidia-smi / NVML** — good for NVIDIA presence + VRAM; Windows-friendly if the driver tools are installed; vendor-specific.
2. **Ollama runner reports** — once Ollama is up, ask what backend it used (GPU vs CPU); reflects real inference path, not just hardware presence.
3. **Capability flag only** — expose `gpu.available` / optional `name` for display; never `if device_name == "..."`. Feature gates check capability, not model SKU (Decision #003 rule 9).

Chosen for now: stub `gpu.available: null` in `/health`; implement after Ollama path is real.

Why it matters: AMD/Intel/CPU-only machines must share the same code path.

### 07/22/2026 � Product rename config + Windows icons

What I learned: Keep display name, company, and version in one `app.config.json`; Electron, Vite HTML title, and electron-builder all read it (with a small `sync-app-config` into `package.json`). For desktop icons, bake a dark background into a multi-resolution `.ico` � PNG alone and light plates look wrong on Windows.

Why it matters: Renaming away from a working title (e.g. MosAIq) is one config edit + repackage, and the shortcut looks intentional.

### 07/23/2026 ? Launcher shell UX (tray, login item, session size)

What I learned:
1. **Tray click vs focus** ? Left-click focuses the tray first, so `isVisible() && isFocused()` never hides. Toggle on visibility for tray; keep focus-aware toggle for Alt+Space.
2. **Login-item readback** ? On Windows, `getLoginItemSettings({ path, args })` must match `setLoginItemSettings` or `openAtLogin` reads false and checkbox rebuilds unchecked. Unpackaged entries show as ?Electron? in Startup apps.
3. **Session vs durable window size** ? For a launcher, resize should stick across Esc/Alt+Space pause, but Quit should return to the default. Cross-session persistence felt sticky without an obvious reset.

Why it matters: Small Electron/OS mismatches read as ?the feature is broken? even when the registry/setting is correct.

### 07/23/2026 ? Watcher ownership (brain vs shell)

What I learned: For a cross-platform Electron + FastAPI app, Chokidar vs Python `watchdog` is not decided by Windows/macOS/Linux support ? both wrap the same OS watchers. The real question is who owns the corpus: ignore rules, queue, and index updates. Putting watching in FastAPI avoids duplicating denylists in Node and survives Electron attach-mode. Polling stays a cold-start safety net, not the primary mode.

Why it matters: Phase 4 can implement one pipeline without rewriting when Max adds a Mac or dual-boots Linux; Decision #005 locks that lean before coding.

### 07/23/2026 ? Visible index confidence

What I learned: Wiring the existing launcher Footer **Indexed** stub to `GET /index/status` gives lasting user confidence without a throwaway debug UI. System Status can host a temporary Browse/Scan control until #40 folder management lands.

Why it matters: Phase 3 steps (DB ? save ? search) need a clear ?it worked? signal on the primary surface.

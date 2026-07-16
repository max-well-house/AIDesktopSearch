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

### 07/14/2026 — GPU detection research (deferred)

Question: How should the app detect hardware acceleration without baking in "RTX 5060 Ti"?

Approaches to evaluate later:

1. **nvidia-smi / NVML** — good for NVIDIA presence + VRAM; Windows-friendly if the driver tools are installed; vendor-specific.
2. **Ollama runner reports** — once Ollama is up, ask what backend it used (GPU vs CPU); reflects real inference path, not just hardware presence.
3. **Capability flag only** — expose `gpu.available` / optional `name` for display; never `if device_name == "..."`. Feature gates check capability, not model SKU (Decision #003 rule 9).

Chosen for now: stub `gpu.available: null` in `/health`; implement after Ollama path is real.

Why it matters: AMD/Intel/CPU-only machines must share the same code path.

# Installation guide

**Supported:** Windows (portable app).  
**Not yet:** macOS, Linux.

Meshen is a local desktop search app. You do not need to clone the repo or create a Python venv to use a release build.

## Get the app

1. Download the Windows portable build from the [GitHub Releases](https://github.com/max-well-house/AIDesktopSearch/releases) page (`Meshen 1.0.3.exe`, or the current `Meshen <version>.exe`).
2. Put it somewhere you can find (e.g. Desktop or a tools folder). No installer required.
3. Double-click to run.

On first launch, Electron starts the bundled FastAPI backend automatically. The search index is stored under the app’s Windows user data folder (not next to the `.exe`).

## First run checklist

1. Launcher opens with the search field focused.
2. Open **Settings** (top-right mark) → add at least one folder you want indexed.
3. Wait for indexing (and optional embedding if Ollama is set up).
4. Type a filename or phrase in the launcher and open a result.

## Optional: Ollama (meaning search)

Classic filename/content search works **without** Ollama.

For **semantic** (meaning) search:

1. Install Ollama separately ([ollama.com/download/windows](https://ollama.com/download/windows), or `winget install --id Ollama.Ollama -e`).
2. Start Ollama from the Start menu / tray.
3. Pull the embed model:

```powershell
ollama pull nomic-embed-text
```

4. In Meshen Settings → **Details**, confirm Ollama and the embedding model look available. The footer **Semantic** light turns green when meaning search is ready.

Ollama is never bundled with Meshen and is never required for basic search.

## Verify

| Check | Where |
|-------|--------|
| Backend up | Settings → Details → API healthy |
| Classic search | Type a known filename substring with no Ollama |
| Semantic | Footer Semantic green after folders embed |
| Quit clean | Tray → Quit; no leftover Python/uvicorn processes |

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| Backend offline / Settings empty | Quit via tray and relaunch the portable exe. Re-download if the build is corrupt. |
| Alt+Space does nothing | Another app may own the hotkey. Meshen falls back to **Ctrl+Shift+Space**. |
| Semantic never goes green | Install/start Ollama, `ollama pull nomic-embed-text`, add/rescan folders, wait for embed queue (Pause if the machine is busy). |
| SmartScreen / antivirus warning | Portable Electron builds are often unsigned; allow the file if you trust the source. |

## Developers

To run from source, see the **Quick start** section in the [README](../README.md) (Python venv + `npm run dev`). Packaging: `npm run package:portable` stages the FastAPI sidecar (Decision #009).

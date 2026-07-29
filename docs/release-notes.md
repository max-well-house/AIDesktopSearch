# Release notes

## v1.0.1 — Hotfix

Patch release for the Windows portable build.

- **Alt+Space** while focused no longer opens the Windows system menu; it toggles/hides the launcher as intended
- **Single-instance** — a second launch focuses the existing app instead of stacking processes
- **Quit cleanup** — tray Quit waits for the owned backend process tree to exit so the portable `.exe` can be deleted/replaced without Task Manager

### Docs

- [Installation](./install.md)
- [User guide](./user-guide.md)

## v1.0.0 — Daily Driver

First storeable **classic + semantic** search release for Windows. Add folders, auto index + auto embed, search, open files, Settings, tray/hotkey chrome.

### Highlights (Phases 1–10)

- Electron + React launcher with mosaic idle brand; search-first (Decision #004)
- FastAPI backend lifecycle from Electron (attach or spawn; clean quit)
- Opt-in folder roots, classic FTS (TXT / Markdown / DOCX / PDF), live watch
- Semantic embeddings via optional Ollama (`nomic-embed-text`) + sqlite-vec
- Hybrid search: classic-first escalate/merge; filename-like stays classic-leaning
- Settings home: folders, auto-watch, Start with Windows, Pause, index wipe, version
- Footer capability lights (Semantic live; AI reserved for v1.1)
- Keyboard navigation, dark chrome / scrollbars, portable packaging
- **Packaged FastAPI sidecar** — no developer Python venv for end users (Decision #009 / #111)

### Known limitations

- **Windows only** — macOS / Linux not packaged yet
- **Ollama is optional and external** — classic search works without it; semantic needs Ollama + embed model
- **No RAG / chat answers** — AI light stays off until v1.1 (#70+)
- **No image / OCR search** — planned for v1.2
- PDF page hints do not jump the reader to that page
- Formats beyond TXT / MD / DOCX / PDF are out of scope for v1.0
- Portable build may trigger SmartScreen until signed
- History, favorites, recent-files chrome demoted to nice-to-have

### Docs

- [Installation](./install.md)
- [User guide](./user-guide.md)

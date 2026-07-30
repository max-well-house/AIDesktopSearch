# User guide

Daily use of Meshen on Windows. For download/setup, see [install.md](./install.md).

## Launch and hide

| Action | Result |
|--------|--------|
| Start the portable exe | Launcher opens (or stays in tray if started hidden with Windows) |
| **Alt+Space** | Show / focus (falls back to **Ctrl+Shift+Space** if Alt+Space is taken) |
| **Escape** | Dismiss launcher and clear the query; app stays in the tray |
| Tray left-click | Show / hide (keeps the query) |
| Tray → Reset window size | Restore default 720×480 and center (no Quit) |
| Tray → Quit | Exit app and stop the owned backend |

Window size sticks for the session. **Tray → Reset window size** restores 720×480 without quitting; **Quit** still cold-starts at the default next launch.

## Search

1. Type in the launcher — results appear as you type.
2. **Classic** search matches filenames and indexed text (TXT, Markdown, DOCX, PDF). No Ollama required.
3. **Semantic** (meaning) search runs when vectors exist and Ollama can embed the query. Hybrid routing prefers classic for filename-like queries and escalates/merges when helpful.
4. Arrow keys move the selection; **Enter** opens the selected file in the OS default app.
5. PDF hits may show a page number; the app does not jump the PDF reader to that page yet.

Clear the field with the search clear control or Escape (dismiss).

## Settings

Open via the top-right **AppMark** (tooltip: Settings).

| Area | What you can do |
|------|------------------|
| Folders | Add / rescan / remove opt-in roots only — nothing is indexed until you choose it. Content search covers TXT, Markdown, DOCX, PDF; other files are filename-only; hidden / junk dirs are skipped |
| Auto-watch | Per-root toggle: watch for changes vs scan-only |
| Start with Windows | Launch at login (also on the tray menu) |
| Prefer semantic | Footer / routing preference when meaning search is available |
| Pause / Resume | Shown while the embedding queue is active (or paused) |
| Privacy | Wipe the search index (recreates `index.db`; your original files are untouched) |
| Details | Lab health: API, Ollama, GPU, vector store, embed model |
| Version | Product name + version at the bottom of Settings |

## Footer lights

| Light | Meaning in v1.0 |
|-------|------------------|
| **Semantic** | Green when meaning search is ready; yellow while preferred but not ready / embedding; off if unavailable |
| **AI** | Stays offline / caution until **v1.1** local RAG answers — not a chat product in v1.0 |

## What “AI” means today

- **v1.0:** local classic + semantic **search** (optional Ollama for embeddings).
- **Not in v1.0:** chat answers, RAG summaries, or cloud LLMs.

See [release-notes.md](./release-notes.md) for known limitations and the v1.1 roadmap.

# Decision #001

## Choice

Electron + React + Python + FastAPI

## Date

July 2026

## Why

- Leverages existing React skills
- Faster MVP development
- Strong AI ecosystem through Python
- Easier Cursor / pair-programming assistance
- Desktop shell is not the performance bottleneck for this product

## Tradeoffs accepted

- Higher baseline RAM usage than Tauri
- Larger app size
- Less native system integration

## Revisit when

- App becomes resource constrained in daily use on the primary machine
- A large user base exists and Electron memory is a proven problem
- Mobile becomes a real requirement

Do not plan a shell migration. Revisit only when forced by real usage.

## Status

Accepted
---

# Decision #002

## Choice

Hybrid search by default

## Date

July 2026

## Why

AI should enhance search, not replace it. Filename and keyword lookup must stay milliseconds-fast. The LLM should only run when the user needs synthesis or reasoning over document contents.

Routing order:

1. Classic filename / keyword search
2. Semantic search (when needed)
3. LLM + citations (when reasoning is needed)

The user should never pay the cost of AI when traditional methods are enough (example: find invoice.pdf).

## Tradeoffs accepted

- Need query routing / intent heuristics
- More moving parts than "always ask the LLM"

## Status

Accepted

---

# Decision #003

## Choice

Operability bar: this machine first, with graceful degradation

## Date

July 2026

## Primary hardware profile

| Spec | Value |
|------|--------|
| CPU | Intel Core i5-14400F @ 2.50 GHz |
| System RAM | 16GB DDR5 |
| GPU | NVIDIA GeForce RTX 5060 Ti (8GB VRAM) |
| Storage | ~1.40 TB total, ~214 GB used |
| OS | Windows |

## Rules

1. Usable every day on the primary profile is non-negotiable.
2. Search must work without AI. If Ollama is missing or unhealthy, classic (and later semantic) search still works.
3. Prefer GPU inference for Ollama on this profile; support CPU-only and no-Ollama as degraded modes.
4. Corpus is opt-in folders ? never whole-disk by default. Denylist noise (node_modules, hidden junk). Indexing is background and pauseable.
5. Cap retrieved chunks. No whole-PC-in-the-prompt.
6. Post-index latency: classic search feels instant; RAG under 1 minute on this machine, aiming for seconds with a VRAM-fitting quantized model.
7. Model size is configurable / machine-tiered. Defaults fit 16GB system RAM + 8GB VRAM beside OS + app + index.
8. Same architecture on weaker/stronger machines via settings ? not forks.
9. Never assume a specific GPU vendor or device name. Hardware detection is **capability-based** (`gpu.available`), not device-name-based (`if RTX 5060 Ti`). Prefer GPU on this profile; the same feature gates must work for AMD, Intel, CPU-only, and future hardware.

## Why

Avoid spending a year building something that demos well elsewhere but is unusable on the machine that matters most ? and still runs (degraded) elsewhere.

## Status

Accepted

---

# Decision #004

## Choice

Launcher-first UI with mosaic as idle brand (not permanent chrome)

## Date

July 2026

## Why

MosAIq is a desktop search engine, not a chatbot. The launcher is the application; search is always the primary interaction. A subtle file-tile mosaic communicates the product metaphor on open ("your digital life as one connected mosaic") and gracefully fades when the user types so the workflow stays as fast and uncluttered as Raycast / Spotlight / PowerToys Run.

AI belongs inside search (and later results), not as a separate chat surface.

## Rules

1. Build production-quality components from the start ? no throwaway placeholder shells.
2. Keep the stable hierarchy: SearchBar ? MosaicCanvas (idle) / results slot ? Footer.
3. Mosaic exists permanently in the tree; visibility is an idle-state concern.
4. Theme tokens live in `frontend/src/theme.js` ? brand palette `#0D1117` / `#00E5A8` / `#22C55E` / `#06B6D4` / `#2563EB` / `#8CA3A0`.
5. Empty states use intentional guidance copy, not generic "No Results".
6. Brand mark is the mosaic M (`MosaIqMark` / favicon); keep window icon and favicon in sync.

## Status

Accepted

---

# Decision #005

## Choice

Filesystem watching via Python `watchdog` inside FastAPI (not Chokidar / Electron)

## Date

July 2026

## Why

- FastAPI is the brain: indexer, ignore rules, SQLite, and the change queue should share one owner (Decision #001 architecture).
- v0.3 scanner work (#40, #45, #46) already defines corpus roots and denylists in Python ? watching must reuse that path, not fork it into Node.
- Electron attach/spawn lifecycle (#96): watching can stay alive with the backend rather than dying when the shell quits in attach scenarios.
- Cross-platform (Windows now; macOS / Linux later) is a wash vs Chokidar ? both wrap FSEvents / inotify / ReadDirectoryChangesW. Preferring Mac or dual-boot Linux does **not** favor Chokidar; it favors keeping the product core in Python.
- Chokidar remains a documented alternate if Python watching proves painful; raw `fs.watch` and hand-rolled OS APIs are rejected; polling is startup / fallback only.

## Tradeoffs accepted

- Watcher status and control need FastAPI endpoints (UI still goes React ? Electron ? API).
- One more Python dependency; Linux large-tree `inotify` limits still apply (mitigate with opt-in roots + denylist, Decision #003).

## Rules for Phase 4

1. Research only until v0.4 ? no watching in v0.3 implementation work.
2. Pipeline: event ? filter ? queue ? debounce/batch ? index worker ? SQLite (never one index job per raw event).
3. Start watching a root only after its initial index pass finishes; on cold start, reconcile then watch.
4. React never watches the filesystem.

## Revisit when

- `watchdog` cannot meet reliability or CPU goals on the primary machine after a real v0.4 spike
- A concrete product need requires the shell to own FS events (unlikely)

Full comparison: [research-filesystem-watchers.md](./research-filesystem-watchers.md).

## Status

Accepted

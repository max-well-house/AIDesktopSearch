# Research: Filesystem watchers (#38)

**Date:** 2026-07-23  
**Milestone:** Research lived in **v0.3.0** (File Indexer); **implementation is v0.4.0** (Live File Watching).  
**Decision:** [#005](./decisions.md) — Python `watchdog` in FastAPI.  
**Status:** Complete (research only — nothing watches files yet).

---

## Goal

Choose how MosAIq should detect file creates, edits, deletes, and renames so Phase 4 can keep the search index fresh without thrashing the machine (Decision #003).

This milestone issue is **research only**. No watcher code ships here.

---

## Framing (important)

| Milestone | What it is |
|-----------|------------|
| **v0.3.0 File Indexer** | Opt-in folders, SQLite filename index, classic search. Watcher research (#38) is one ticket inside this phase. |
| **v0.4.0 Live File Watching** | Implement watching + auto-update SQLite (#48–#52). |

Do not treat “pick a watcher” as the Phase 3 product goal. Phase 3 success remains: user folders → filename search without Ollama.

---

## Options compared

### 1. Python `watchdog` (chosen)

Cross-platform Python library used by many indexing / sync tools. Wraps:

- Windows → `ReadDirectoryChangesW`
- macOS → FSEvents
- Linux → inotify

**Pros**

- Lives next to the indexer, ignore rules, and SQLite updates
- Matches architecture: Electron = shell, FastAPI = brain
- Same ignore / path-normalization code path as the v0.3 scanner (#40, #45, #46)
- Works if Electron **attaches** to an already-running uvicorn (#96) — watching can stay with the brain
- Cross-platform (Windows now; macOS / Linux later without rewriting the watcher)

**Cons**

- Extra Python dependency
- Watcher status still needs an API surface for the React UI
- Same OS limits as every other native watcher (e.g. Linux `inotify` max watches)

**Fit:** Best long-term fit for this repo.

### 2. Chokidar (Electron / Node) — strong alternate

Mature Node watcher; common in Electron apps. Same native backends under the hood.

**Pros**

- Excellent docs and community; recursive + rename handling is battle-tested
- Polling fallback built in
- Natural if the desktop process is the only long-lived process

**Cons**

- Puts filesystem ownership in the “dumb shell”
- Risk of duplicating denylist / path rules in Node and Python
- In attach mode, quitting Electron stops watching even if uvicorn keeps running
- Cross-platform story is not better than `watchdog` (same OS APIs)

**Fit:** Fine for generic Electron apps; **not** preferred here. Keep as documented fallback if Python watching proves painful in practice.

### 3. Node `fs.watch` / `fs.watchFile`

Built-in; no dependency.

**Pros:** Lightweight, no package.  
**Cons:** Behavior differs by OS; recursive / rename handling inconsistent; misses events.  
**Fit:** Rejected for production incremental indexing.

### 4. Polling (scan + compare mtimes)

**Pros:** Simple; works everywhere; good for **startup reconciliation** and as a safety net.  
**Cons:** CPU, disk, and battery cost; scales poorly as primary mode.  
**Fit:** Fallback / cold-start catch-up only — not the primary watcher.

### 5. Raw OS APIs (`ReadDirectoryChangesW` / FSEvents / inotify)

**Pros:** Maximum control, lowest overhead.  
**Cons:** Three implementations, hard maintenance.  
**Fit:** Overkill for MVP (not building Everything / Spotlight).

---

## Comparison matrix

| Feature | watchdog | Chokidar | fs.watch | Polling | Raw OS APIs |
|---------|----------|----------|----------|---------|-------------|
| Cross-platform | Yes | Yes | Partial | Yes | No (per-OS) |
| Reliable enough for MVP | Yes | Yes | Risky | Yes (slow) | Yes |
| Recursive watching | Yes | Yes | Partial | Yes | Depends |
| Rename handling | Good | Good | Weak | Via rescan | Good |
| Fits “FastAPI = brain” | **Yes** | Weak | Weak | Neutral | Neutral |
| Shares ignore rules with indexer | **Yes** | Duplicate risk | Duplicate risk | Yes | Yes |
| Easy to implement | Yes | Yes | Yes | Yes | No |
| Primary choice | **Yes** | Alternate | No | Fallback only | No |

macOS and Linux later **do not** change this ranking: both `watchdog` and Chokidar wrap the same native mechanisms. Preferring Mac / dual-boot Linux reinforces keeping the brain portable in Python — it does not favor Chokidar.

---

## Architecture for Phase 4

Responsibilities:

```
Electron          React
  (shell)          (status / progress UI only)
     |
     |  existing IPC → HTTP gatekeeper
     v
FastAPI
  - opt-in folder roots
  - ignore rules
  - watchdog observers
  - change queue + debounce / batch
  - index worker
  - SQLite (later vectors)
     |
     v
Filesystem (user-selected trees only)
```

Event pipeline (do **not** re-index on every raw OS event):

```
Filesystem event
       │
       v
  Normalize + filter
  (roots, denylist, temp/hidden rules)
       │
       v
  Enqueue path + event kind
       │
       v
  Debounce / coalesce
  (e.g. editor save storms, git checkout)
       │
       v
  Batch index worker
       │
       v
  Update SQLite
```

Example: several `modify` events on one file within ~1s → **one** index update.

Mass change example: `git checkout` touching thousands of files → queue all, process in batches, never spawn one job per event.

---

## Requirements captured for Phase 4

### What to watch

- User-selected corpus folders only (Decision #003; #40)
- Apply the same denylist as the scanner (`node_modules`, `.git`, `venv`, etc. — #46)
- Ignore hidden / system junk unless the user opts in (#45)
- Ignore editor temp / lock files where practical

### Events that matter

| Care about | Usually ignore |
|------------|----------------|
| File created / modified / deleted | Access-time only |
| File renamed | Permission-only changes (unless needed later) |
| Folder created / deleted | |

### Lifecycle

- **Do not** start watching until the initial (or folder-add) index pass for that root has finished — avoids duplicate work.
- **While app / backend is down:** no live events. On startup: **quick reconciliation scan** (mtime / presence vs SQLite), then resume watching.
- **Pause / resume indexing** (Decision #003): pausing should stop or drain the watcher queue without freezing the UI (#52).
- Removable / external drives: treat disconnect as deletes or “unavailable”; do not assume network / cloud folders are reliable in v0.4 (document as known risk).

### Scale bar

Design for Decision #003’s machine and opt-in trees — not “whole disk / millions of files on day one.” Linux `inotify` watch limits matter for huge trees either way; the fix is fewer watched roots and ignore rules, not a different library.

---

## Out of scope (this research)

- Implementing any watcher
- Embedding / semantic re-index on change (later phases)
- Cloud folder sync (#103 nice-to-have)

---

## See also

- Decision [#005](./decisions.md)
- [architecture.md](./architecture.md) — planned live-watching flow
- [roadmap.md](./roadmap.md) — v0.3.0 vs v0.4.0
- Issues: #38 (research), #48–#52 (v0.4 implementation)

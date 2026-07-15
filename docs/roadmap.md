# Version 0.0.1

Foundation

Repo, board, docs, folder structure

Status: done (repo layout, GitHub board/milestones/issues, core docs)

---

# Version 0.0.2

Architecture Spike

Prove React → Electron → FastAPI → hello → UI (Ollama optional)

Status: in progress (2026-07-14)

- [x] Electron desktop window boots (`npm start` / `npm run dev`)
- [x] FastAPI status endpoint (`GET /` → status, version, timestamp, message)
- [x] Electron main process calls local FastAPI and surfaces result or connection error
- [x] React in the renderer (Vite) — Backend Connection Test via Electron IPC
- [ ] Material UI
- [ ] Ollama optional / health (nice-to-have for this spike)

---

# Version 0.1.0

Desktop Shell

Native window, React UI, FastAPI lifecycle

---

# Version 0.2.0

Search Launcher

Global shortcut, tray, Escape

---

# Version 0.3.0

File Indexer

Opt-in folders, SQLite filename search, hybrid routing stub

---

# Version 0.4.0

Live File Watching

Auto-update index

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

Embeddings / meaning search (defaults fit 16GB + 8GB VRAM)

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

Settings, polish, guides

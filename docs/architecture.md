# Architecture

```
                 User
                  |
            Electron App
                  |
        --------------------
        |                  |
     React UI          Node Main
        |                  |
        --------------------
                  |
              FastAPI
                  |
      ------------------------
      |          |           |
  Indexer    Search       AI Engine
      |          |           |
  SQLite    Vector DB    Ollama
      |
  Filesystem
```

Electron is a dumb shell (window, tray, shortcuts, packaging).
FastAPI is the brain (indexing, search, AI).
Ollama is a separate process — never parented directly under Electron.

---

## Query routing (Decision #002)

```
Question comes in
       |
       v
Can classic search answer this?
       |
   Yes --------> Return instantly
       |
       No
       v
Use semantic search
       |
Need reasoning?
       |
       v
Ask LLM (with citations)
```

---

## Operability modes (Decision #003)

| Mode | When | Capabilities |
|------|------|----------------|
| Classic only | Ollama unavailable / RAM tight / AI off | Filename + keyword search |
| Classic + semantic | Vectors ready | Meaning search without LLM |
| Full RAG | Ollama healthy + user asks | Answers with citations |

Degrade cleanly. Never crash because AI is missing.

---

## Primary hardware profile

| Spec | Value |
|------|--------|
| CPU | Intel Core i5-14400F @ 2.50 GHz |
| System RAM | 16GB DDR5 |
| GPU | NVIDIA GeForce RTX 5060 Ti (8GB VRAM) |
| Storage | ~1.40 TB total, ~214 GB used |
| OS | Windows |

- System RAM budget: OS + Electron + FastAPI + index working set
- VRAM budget: local models via Ollama (prefer GPU on this profile)
- Weaker machines: classic/semantic; smaller or no local LLM
- Stronger machines: larger models via settings, same architecture

See Decision #003.

---

## Frontend

React

Electron

Material UI

## Backend

Python

FastAPI

SQLite

Ollama

Chroma

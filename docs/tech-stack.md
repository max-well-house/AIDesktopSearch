# Roles

- Electron: dumb desktop shell (window, tray, shortcuts, packaging)
- React + Material UI: UI
- FastAPI: brain (index, search, AI)
- Ollama: separate process for local models (never inside Electron)
- Defaults sized for the primary profile (16GB system RAM + 8GB VRAM). Exact models chosen later against Decision #003.

# Frontend

## React

Why?

Already familiar

---

## Electron

Why?

Cross platform

See Decision #001 (Electron + React + Python + FastAPI)

---

## Material UI

Why?

Ready-made components for a consistent React UI

# Backend

## Python

Why?

AI ecosystem

---

## FastAPI

Why?

Simple local API for the desktop app backend

---

## SQLite

Why?

Simple

No server required

---

## Ollama

Why?

Local models

Separate process; prefer GPU on the primary machine

---

## Chroma

Why?

Local vector store for embeddings / semantic search

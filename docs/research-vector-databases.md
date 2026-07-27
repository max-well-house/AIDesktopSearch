# Research: Vector databases (#64)

**Date:** 2026-07-27  
**Milestone:** Research inside **v0.7.0** (Semantic Search); **implementation is #67** (store), fed by #66 (generate) and #68 (search).  
**Decision:** [#008](./decisions.md) — **sqlite-vec** as the primary local vector store (same SQLite brain as `files` / FTS5).  
**Status:** Research complete. Recommendation recorded. No store code ships here.

---

## Goal

Compare vector storage options for MosAIq as a **local desktop** app (Electron + FastAPI + existing SQLite), and pick a default that fits Decisions [#001](./decisions.md), [#002](./decisions.md), [#003](./decisions.md) and the embeddings notes in [research-embeddings.md](./research-embeddings.md) (#63).

This issue is **research only**. No vector tables or extension loading land here.

---

## Framing (important)

| Milestone | What it is |
|-----------|------------|
| **#63 Learn embeddings** | What vectors are; local vs cloud; generate ≠ query. |
| **#64 Compare vector DBs** | Where vectors live on disk / in-process for this desktop app. |
| **#66–#68** | Generate, store, semantic endpoint. |
| **#69 Hybrid** | Merge classic FTS + vector hits. |

Corpus is **opt-in folders**, not whole-disk (Decision #003). Expect tens of thousands of chunks for a daily-driver personal library, not a multi-tenant cloud RAG farm. Classic FTS already lives in SQLite. Ollama stays a **separate** optional process — the vector store should not invent a second always-on server.

Do not treat “pick a vector DB” as designing cloud SaaS retrieval or replacing FTS5.

---

## Criteria (local desktop)

| Criterion | Why it matters here |
|-----------|---------------------|
| In-process / no extra daemon | Matches FastAPI = brain; Electron attach mode; Decision #003 lean ops |
| Persistence next to corpus index | One backup / wipe story with `index.db` (#114 later) |
| Join / map to `files` (+ page) | Semantic hits must open the same paths as classic |
| Hybrid-friendly | #69 wants classic + semantic without two unrelated systems |
| Packaging on Windows | Wheels / native bits must be shippable with the Python sidecar (#111) |
| Scale for opt-in personal corpus | Exact k-NN OK if ANN not needed at our size |
| License | Prefer permissive; avoid growing AGPL surface beyond PyMuPDF |
| Fits 16GB RAM + 8GB VRAM bar | Store should not fight Ollama for RAM |

---

## Options compared

### 1. sqlite-vec (chosen)

SQLite extension (`vec0` virtual tables). Vectors live in (or beside) the same DB file as metadata / FTS. Exact (brute-force) k-NN in stable releases; ANN experiments exist but are not the foundation.

**Pros**

- Same process and ownership as the indexer (`files`, `file_content`, FTS5)
- SQL joins from chunk → `file_id` / page are natural
- No second database product; backup / `AIDESKTOP_DB` story stays one file (or one folder with a known extension load)
- MIT / Apache dual — packaging-friendly vs AGPL creep
- Exact search is fine for opt-in personal corpora (Decision #003)
- Hybrid (#69): FTS5 + vec in one engine — app-level fusion stays simple

**Cons**

- Must **load a native extension** (Windows DLL) — packaging detail for #67 / #111
- Stable path is brute-force (cost grows with chunk count); revisit if corpus grows huge
- Younger project (v0.1.x) — pin versions; have a documented escape hatch
- Less “RAG DX” sugar than Chroma (we own chunk metadata tables)

**Fit:** Best primary store for MosAIq’s architecture.

### 2. Chroma (provisional tech-stack placeholder — demoted)

Embedded (or client/server) vector DB popular for Python RAG prototypes. Collections, metadata filters, HNSW.

**Pros:** Fast prototype DX; approximate search out of the box; Python-first.  
**Cons:** Separate store from SQLite; more moving parts and RAM pressure; duplicates “source of truth” for chunk→file maps; overshoots lean desktop ops.  
**Fit:** Rejected as primary. Acceptable mental model for prototypes only — not the shipped default.

### 3. LanceDB

Embedded library on the Lance columnar format. Disk-friendly ANN, versioning, optional native hybrid FTS+vector.

**Pros:** Scales past RAM; strong embedded “real vector engine”; Apache-2.0 core.  
**Cons:** Second storage format (directory, not our SQLite file); hybrid FTS would compete with or duplicate existing FTS5; heavier concept surface for v0.7.  
**Fit:** Documented **escape hatch** if sqlite-vec brute-force or packaging fails after a real #67 spike — not the default.

### 4. FAISS (library, not a DB)

Meta’s similarity-search library. Excellent indexes; persistence and metadata are DIY.

**Pros:** Battle-tested k-NN / ANN.  
**Cons:** We would reinvent store, file maps, and lifecycle next to SQLite.  
**Fit:** Rejected as primary product store; fine as an internal algorithm reference.

### 5. Qdrant / other servers

Dedicated vector DB (local Docker or cloud).

**Pros:** Production ANN, filters, scale.  
**Cons:** Extra daemon fights Decision #003 and “no Ollama required for classic”; terrible default for a launcher app.  
**Fit:** Rejected for defaults. Cloud vector APIs same rejection as cloud embeddings default (#63).

### 6. Raw SQLite BLOB + NumPy scan

Store `float32` blobs; brute-force in Python.

**Pros:** Zero extension load.  
**Cons:** We rebuild what sqlite-vec already is; worse SQL ergonomics.  
**Fit:** Fallback only if extension loading is impossible on a target platform.

### 7. Rejected class

| Option | Why rejected |
|--------|----------------|
| Pinecone / Weaviate cloud | Breaks local-first; keys; network on every semantic query |
| pgvector | Requires Postgres — not our stack |
| DuckDB VSS | Second analytical engine; we already committed to SQLite |
| LangChain vector wrappers as core | Framework ownership; Decision #006/#007 spirit |

---

## Comparison matrix

| Criterion | sqlite-vec | Chroma | LanceDB | FAISS | Qdrant server |
|-----------|------------|--------|---------|-------|---------------|
| Extra daemon | **No** | No (embedded) / optional server | **No** | No | **Yes** |
| Same file as `index.db` | **Yes** (extension) | No | No (Lance dir) | DIY | No |
| Join to `files` / FTS | **Natural SQL** | App-level | App-level | DIY | App-level |
| ANN at huge scale | Weak (stable = exact) | HNSW | **Strong** | Strong | Strong |
| Personal corpus fit | **Excellent** | OK | Overkill early | Awkward | Overkill |
| Windows packaging | Extension DLL | Pip + native | Pip + native | Pip + native | Service |
| License | MIT/Apache | Apache-2.0 | Apache-2.0 | MIT | Apache-2.0 |
| Primary choice | **Yes** | No | Escape hatch | No | No |

---

## Architecture for Phase 7 store (#67)

```
file_content (existing text)
       │
       v
chunk + embed (#66)  →  vectors + chunk metadata
       │
       v
sqlite-vec (vec0) in / beside index.db   (#67)
       │
       +---- FTS5 (classic, already shipped)
       │
       v
semantic k-NN (#68)  +  hybrid merge (#69)
```

```
FastAPI indexer / search
  - load sqlite-vec once at DB open
  - chunk rows: file_id, page?, model_id, dim, text preview?
  - vec0 holds embeddings
  - DELETE file / remove root cascades chunk+vector cleanup
```

**Not in #64:** chunk sizes, model SKU, hybrid rank formula, Ollama install.

---

## Requirements captured for #67 (and neighbors)

### Store (#67)

- Persist embeddings with stable map to `files` (and page when present)
- Record `model_id` + dimension (do not mix models in one collection without re-embed)
- Soft-fail missing extension / load errors — classic search still works
- Schema bump + `docs/schema.md` update
- Delete/orphan cleanup when files or roots go away

### Generate (#66) / search (#68)

- Write path and query path share the same store API
- Semantic query works when vectors exist even if Ollama is down (#63)

### Packaging (#111)

- Ship or document how the sqlite-vec binary loads on Windows next to the frozen/venv Python

### Revisit → LanceDB (or similar)

- Brute-force k-NN too slow on a real Max corpus after opt-in growth
- Extension loading blocked on a supported OS
- Product need for disk-ANN / versioned datasets that SQLite cannot meet

---

## Recommendation

**Primary: sqlite-vec** inside the FastAPI SQLite brain.

**Demote** the tech-stack Chroma placeholder.  
**Escape hatch:** LanceDB if forced by scale or packaging.  
**Never default:** cloud / server vector DBs.

Full lock: Decision [#008](./decisions.md).

---

## Explicitly out of scope for #64

- Implementing vec tables or extension load (#67)
- Choosing the embedding model (#65 / #66)
- Hybrid ranking (#69)
- Cloud vector SaaS as a product mode

---

## Open questions (hand off)

1. **#67:** Load extension how on Windows (path next to `index.db` vs package data)? Single DB file vs sidecar `.vec.db`?
2. **#67:** Chunk metadata tables vs only `vec0` auxiliary columns?
3. **#66:** When does exact k-NN feel slow on the primary machine (measure; don’t guess forever)?
4. **#69:** Fuse FTS rank + cosine in SQL, or merge in Python?

---

## References

- Embeddings context: [research-embeddings.md](./research-embeddings.md) (#63)
- Decisions: [#001](./decisions.md), [#002](./decisions.md), [#003](./decisions.md), [#008](./decisions.md)
- Schema “not yet”: [schema.md](./schema.md)
- Prior research style: [research-pdf-libraries.md](./research-pdf-libraries.md)
- Issues: #64 (research), #67 (store), #66 / #68 / #69 (neighbors)

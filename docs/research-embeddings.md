# Research: Embeddings (#63)

**Date:** 2026-07-27  
**Milestone:** Research inside **v0.7.0** (Semantic Search); **implementation is #65–#69** (plus #112 GPU detection).  
**Decision:** None yet — learning notes only. Vector store → [research-vector-databases.md](./research-vector-databases.md) / Decision #008. Model install → #65.  
**Status:** Research complete (notes). No embedding or chunking code ships here.

---

## Goal

Understand how embeddings enable meaning search for MosAIq’s local desktop corpus, and capture local vs cloud implications under Decisions [#002](./decisions.md) and [#003](./decisions.md).

This issue is **research only**. No embedding models, chunkers, or vector tables land here.

---

## Framing (important)

| Milestone | What it is |
|-----------|------------|
| **v0.5–v0.6** | Classic content search: extract → `file_content` / FTS5 → keyword hits (+ page for PDF). |
| **v0.7.0 Semantic Search** | Chunk → embed → store → nearest-neighbor search; hybrid ranking (#69). Research (#63) + vector DB compare (#64) gate implementation. |
| **v0.8.0 Local AI** | RAG answers + citations — uses retrieval; does not redefine embeddings. |

Do not treat “learn embeddings” as picking Chroma, installing Ollama, or designing hybrid rankers. Phase 7 success remains: **search by meaning on opt-in folders**, defaults fit **16GB RAM + 8GB VRAM**, classic path never depends on AI.

---

## What an embedding is (this product)

An **embedding** is a fixed-length list of numbers (a vector) that represents a piece of text so that **similar meaning ≈ nearby vectors**.

Example:

| Text | Classic FTS | Embedding similarity |
|------|-------------|----------------------|
| Query: “quarterly revenue summary” | Needs those words (or stems) in the file | Can match a doc titled `Q3-P&L-notes.md` that talks about “earnings for the third quarter” |
| Query: `invoice.pdf` | Filename / exact tokens win in milliseconds | Unnecessary — classic should answer (Decision #002) |

MosAIq already stores searchable body text. Embeddings add a **second index** over chunks of that text (and later, optionally, over queries at search time). They do **not** replace FTS or filenames.

---

## Pipeline for MosAIq

Text already exists from the indexer (`file_content` / pages). Semantic path:

```
Extracted text (PDF / DOCX / TXT / MD — already shipped)
       │
       v
Chunk (size + overlap — product knob; not chosen in #63)
       │
       v
Embed each chunk  (#66 — needs a model runner, usually Ollama)
       │
       v
Store vectors + chunk→file(/page) map  (#67 — store choice in #64)
       │
       v
At query time: embed query → k nearest chunks → files  (#68)
       │
       v
Hybrid with classic  (#69)
```

```
Electron          React
  (shell)          (launcher / results)
     |
     |  existing IPC → HTTP
     v
FastAPI
  - classic: FTS / filenames (always)
  - semantic: embed query + vector search (when vectors ready)
  - optional: Ollama for generate + query embed (#65)
```

**Not in #63:** store product pick, Ollama install, schema tables, API shape, hybrid heuristics.

Eventual north star stays: File → Parser → text → Chunker → Embeddings → Vector store, without rewriting classic extract (Decision #006 / #007).

---

## Chunking (name the knob; defer the numbers)

Embeddings are almost never over whole files:

- Long docs exceed model context and dilute meaning.
- Hits should map back to a **file** (and **page** when we have page-scoped text).

Typical desktop-search defaults (to validate in #66, not lock here):

| Knob | Why it matters |
|------|----------------|
| Chunk size (tokens/chars) | Too big → muddy vectors; too small → lose context |
| Overlap | Softens cuts mid-sentence / mid-section |
| Unit | Prefer page-aware chunks for PDFs when page text exists; paragraph/heading splits for MD/DOCX when cheap |

Re-embed on content change (scan/watch modify), same ownership as FTS refresh — do not fork a second corpus pipeline.

---

## Similarity search (concept only)

At query time:

1. Turn the user query into one vector with the **same embedding model** used at index time.
2. Find the **k** stored chunk vectors closest to it (cosine similarity or equivalent).
3. Map chunks → `files` rows (and page when available).
4. Dedupe / rank for the launcher.

Model identity matters: mixing embedding models (or dimensions) in one store corrupts nearest-neighbor results. Persist `model_id` + dimension with the index when #67 lands.

---

## Local vs cloud models

Vision: **local by default**; cloud optional and explicit.

| Dimension | Local (e.g. Ollama embedding model) | Cloud embedding API |
|-----------|--------------------------------------|---------------------|
| Privacy | Text stays on device | Chunks leave the machine |
| Offline | Works after model pull | Needs network |
| Cost | Hardware time / power | Per-token or per-request $ |
| Latency (index) | Bound by CPU/GPU; background + pauseable (Decision #003) | Network + rate limits |
| Latency (query) | Small embed + local k-NN — usually fine for launcher | Extra RTT on every semantic query |
| Quality | Good enough with modern small embed models | Often stronger; not required for v0.7 MVP |
| Ops | Install/detect Ollama (#65); GPU preferred (#112); CPU fallback | API keys, billing, outages |
| Packaging | User installs Ollama (or later we document it); app never parents Ollama under Electron | Keys in settings; never default-on |

### Implications for Decision #003

1. **Generate vs query are different.** Building embeddings needs a live embedder (usually Ollama). **Searching over already-stored vectors does not** — matches architecture’s “Classic + semantic when vectors ready” and Decision #003 rule 2 (“later semantic search still works” when Ollama is down).
2. **Defaults fit 16GB + 8GB VRAM.** Embedding models are typically **much smaller** than chat LLMs. Prefer a small local embed model so Phase 7 does not wait on a large chat model (chat is v0.8).
3. **Cloud is an explicit upgrade path**, not the default index path. If offered later: opt-in, clear copy that text leaves the device, and never block classic search when the API is missing.
4. **Capability Principle.** `/health` already stubs `models.embedding`. When #65/#66 land, report whether embedding generation is available; semantic *query* capability can be “vectors present” even if generation is offline.
5. **Same architecture, tiered settings** — weaker machines: smaller model or classic-only until vectors exist; stronger machines: larger embed model via settings, same pipeline.

### Recommendation (direction, not a locked Decision)

- **Default path:** local embeddings via Ollama (or equivalent local runner), sized for the primary profile.
- **Cloud embeddings:** deferred / optional; not required to close #66–#68.
- **Exact model name / dimension:** choose in #65/#66 against VRAM headroom and quality spikes — out of scope for #63.

---

## How this differs from classic search and from RAG

| Layer | Job | Needs embeddings? | Needs chat LLM? |
|-------|-----|-------------------|-----------------|
| Classic (shipped) | Filename + keyword / FTS | No | No |
| Semantic (v0.7) | Meaning → files/chunks | Yes | No |
| RAG (v0.8) | Answer + citations | Usually yes (retrieve then generate) | Yes |

Decision #002 order stays: classic → semantic when needed → LLM when reasoning is needed. Embeddings unlock the middle rung only.

---

## Failure modes / operability

| Case | Expected behavior |
|------|-------------------|
| Ollama missing | Classic search works; no new embeddings generated; existing vectors still searchable if present |
| Embed model not pulled | Capability = generation unavailable; do not crash API |
| Empty / scanned PDF (no text) | Nothing useful to embed (same soft-fail as FTS) |
| Huge corpus | Background, pauseable embed queue; leave headroom for OS + app (Decision #003) |
| File deleted / root removed | Delete or orphan-cleanup vectors with file rows (#67 design) |
| Model change | Re-embed corpus (version the index); do not mix dims |

---

## Requirements captured for later Phase 7 issues

### Learn / notes (#63) — this doc

- [x] How embeddings work for MosAIq (chunk → vector → k-NN → file)
- [x] Local vs cloud implications under #002 / #003

### Vector store (#64)

- Compare options for a **local desktop** app (process model, persistence next to SQLite, packaging)
- Recommendation recorded (`docs/research-vector-databases.md` / Decision #008 — sqlite-vec)

### Ollama (#65)

- Install / docs for local dev
- App detects/connects; embedding capability surfaced

### Generate (#66)

- Chunk + embed on index/update; pauseable; model id recorded

### Store (#67)

- Persist vectors + chunk metadata; schema bump (`docs/schema.md`)

### Endpoint (#68)

- Semantic search API; plugs `run_semantic` in `backend/search/routing.py`

### Hybrid (#69)

- When to escalate from classic; merge/rank results

### GPU (#112)

- Capability beyond stub so GPU-preferred defaults are honest

---

## Explicitly out of scope for #63

- Choosing Chroma vs sqlite-vec vs others (#64)
- Installing Ollama or pulling a model (#65)
- Chunk size numbers, schema DDL, or API contracts
- Hybrid ranking heuristics (#69)
- OCR / image embeddings (v0.9)
- LangChain / heavy RAG frameworks as the core path
- Embedding during parse (still deferred; extract stays thin)

---

## Open questions (hand off)

1. **#67:** sqlite-vec load path on Windows; single DB vs sidecar; chunk metadata shape?
2. **#66:** Default chunk size/overlap and page-aware strategy for PDFs?
3. **#65/#66:** Which embedding model fits 8GB VRAM with OS + Electron + FastAPI (+ optional later chat)?
4. **#69:** Escalate to semantic on empty classic hits only, or also on “question-shaped” queries?

---

## References

- Decisions: [#002](./decisions.md) (hybrid), [#003](./decisions.md) (operability)
- Architecture: query routing + operability modes
- Schema: chunks/embeddings explicitly “not yet” in [schema.md](./schema.md)
- Prior research style: [research-pdf-libraries.md](./research-pdf-libraries.md), [research-filesystem-watchers.md](./research-filesystem-watchers.md)
- Issues: #63 (research), #64 (vector DBs), #65–#69 / #112 (v0.7 implementation)

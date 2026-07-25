# Research: PDF libraries (#53)

**Date:** 2026-07-24  
**Milestone:** Research inside **v0.5.0** (PDF Reading); **implementation is #54–#57**.  
**Decision:** [#006](./decisions.md) — PyMuPDF in FastAPI; thin per-page extract contract.  
**Status:** Research complete; extract/FTS code not shipped here.

---

## Goal

Choose how MosAIq should extract text from PDFs so Phase 5 can search inside documents without thrashing the machine (Decision #003) and without pulling embeddings or OCR into the critical path (Decision #002).

This issue is **research only**. No PDF parsing code ships here.

---

## Framing (important)

| Milestone | What it is |
|-----------|------------|
| **v0.5.0 PDF Reading** | Extract PDF text, store it, classic search inside PDFs, page hints (#54–#57). Research (#53) is one ticket inside this phase. |
| **v0.6.0 Documents** | DOCX / TXT / Markdown — multi-format parsers earn their keep here. |
| **v0.7.0 Semantic Search** | Chunks / embeddings — after classic content search works. |
| **v0.9.0 Images** | OCR / scanned PDFs — conditional enhancement, not default. |

Do not treat “pick a PDF library” as designing the forever multi-format ingestion platform. Phase 5 success remains: text PDFs → searchable content (+ page) without Ollama.

---

## Options compared

### 1. PyMuPDF (`pymupdf`) (chosen)

Bindings to MuPDF. Fast text extract, metadata, page count, per-page APIs, optional page render (useful later for OCR/thumbnails).

**Pros**

- Strong speed on large corpora (Decision #003 background indexing)
- **Per-page extract** unlocks #57 without a redesign
- Wheels on Windows; fits FastAPI sidecar packaging story
- Lives next to indexer, ignore rules, scan/watch (Decision #001 / #005)

**Cons**

- **AGPL** (or commercial license) — must stay visible for distribution (#111)
- Native binary in the dependency tree (heavier than pure Python)

**Fit:** Best primary library for v0.5.

### 2. pypdf

Pure-Python PDF toolkit (BSD-style permissive license).

**Pros:** Permissive license; no native wheel drama; easy to vendor.  
**Cons:** Slower / weaker layout than PyMuPDF; per-page is fine but not the performance pick for daily indexing.  
**Fit:** Alternate if AGPL becomes a hard blocker; not preferred for Phase 5.

### 3. pdfminer.six

Mature text extraction (MIT).

**Pros:** Solid text; permissive; well known.  
**Cons:** Slower; API less convenient for “index every PDF under opt-in roots.”  
**Fit:** Rejected as primary; acceptable reference for text-quality comparisons.

### 4. pdfplumber

Built on pdfminer; strong at **tables**.

**Pros:** Better table structure when invoices/statements matter.  
**Cons:** Not needed for Phase 5 ACs; extra path complexity.  
**Fit:** Optional later specialty path — never the default parser.

### 5. Rejected class (do not adopt for core)

| Option | Why rejected |
|--------|----------------|
| MarkItDown / Docling / Unstructured | Heavy “RAG pipeline” deps; fight Decision #003; overshoot Phase 5 |
| LangChain PDF loaders | Framework ownership of parsing; we need classic indexing first |
| poppler `pdftotext` CLI | Extra native install; packaging pain on Windows (#111) |
| Electron / PDF.js extract | Puts content ownership in the shell; duplicates brain |
| Cloud parsers (LlamaParse, etc.) | Breaks local-first / offline classic search |

---

## Comparison matrix

| Criterion | PyMuPDF | pypdf | pdfminer.six | pdfplumber |
|-----------|---------|-------|--------------|------------|
| Speed (index many PDFs) | **Best** | OK | Slower | Slower |
| Text accuracy (typical text PDFs) | **Strong** | Good | Strong | Strong |
| Per-page extract (#57) | **Excellent** | Yes | Yes | Yes |
| License | AGPL / commercial | Permissive | MIT | MIT |
| Windows wheels / packaging | **Good** | Easy (pure) | Easy | Easy |
| Tables | Basic text | Basic | Basic | **Best** |
| Fits “FastAPI = brain” | **Yes** | Yes | Yes | Yes |
| Primary choice | **Yes** | Alternate | No | Later specialty |

---

## Failure modes (all libraries)

| Case | Expected Phase 5 behavior |
|------|---------------------------|
| Normal text PDF | Extract per-page text; store; searchable |
| Scanned / image-only | Near-empty text → soft-fail with warning; **do not** run OCR in v0.5 |
| Encrypted / locked | Soft-fail; skip content; leave filename metadata intact |
| Corrupt / unreadable | Soft-fail; do not crash scan/watch batch |
| Huge file | Bound work (timeouts / size caps can land in #54/#58); never block UI |

---

## Architecture for Phase 5

Thin path only:

```
PDF file
   │
   v
PyMuPDF extract (per page)
   │
   v
SQLite content + FTS  (#55)
   │
   v
Classic search hit (+ page)  (#56 / #57)
```

```
Electron          React
  (shell)          (results / open / page hint UI)
     |
     |  existing IPC → HTTP gatekeeper
     v
FastAPI indexer
  - reuse scan + watchdog paths
  - PyMuPDF extract on .pdf create/modify
  - soft-fail empty/scanned
  - SQLite metadata (existing) + content/FTS (new in #55)
```

**Not in v0.5:** chunker → embeddings, OCR, table specialty parser, multi-format `DocumentParser` registry, LangChain.

Eventual north star (v0.6–v0.7+) can grow to File → Parser → normalized text → Chunker → Embeddings without rewriting Phase 5 if extract stays library-agnostic behind a small function/interface.

---

## Requirements captured for Phase 5 (#54–#57)

### Extract (#54)

- Common text-based PDFs yield usable text
- Failures are soft (warnings / empty content), never crash the index worker
- Prefer **per-page** strings (or page offsets) from day one

### Store (#55)

- Extracted text associated with the existing `files` row
- Re-parse when scan/watch sees modify (mtime / event) — extend indexer ownership; do not fork a second pipeline
- Schema bump when content/FTS tables land (`docs/schema.md`)

### Search (#56)

- Queries match PDF body text, not only filenames
- Classic / FTS path; no Ollama required (Decision #002 / #003)
- Results still identify the file

### Pages (#57)

- Hits can surface page (or range)
- User can jump toward the matching location (UI/open details later)

### Performance (#58)

- Batching / measurable improvement notes after extract exists — not part of this research ticket

---

## Out of scope (this research)

- Implementing any PDF parser or schema migration
- OCR / image PDFs (v0.9)
- DOCX / Markdown / email parsers (v0.6+)
- Embeddings / chunking (v0.7)
- Multi-format plugin registry
- Adding `pymupdf` to `requirements.txt` (lands with #54)

---

## See also

- Decision [#006](./decisions.md)
- [architecture.md](./architecture.md) — PDF content stub
- [roadmap.md](./roadmap.md) — v0.5.0
- [tech-stack.md](./tech-stack.md) — PyMuPDF planned
- Issues: #53 (research), #54–#58 (v0.5 implementation)

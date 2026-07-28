# Embed / semantic search audit — 2026-07-28

Correctness audit of the embedding + semantic pipeline (nomic-embed-text → 768-d cosine sqlite-vec → query embed → k-NN → hybrid). **No product routing changes in this pass** — measure and document only.

## Verdict

**Pipeline setup: PASS.** Model, dimension, store, smoke, and forced-semantic retrieval are aligned. Automated suite green. Live corpus proves index↔query model match.

**Product gaps (not pipeline failures):** auto mode skips semantic for ≤2 short tokens (`pokemon`, `fire dragon`), so meaning relatives (e.g. `Charizard.docx` / piplup) only appear when the user forces `mode=semantic` or types a longer hybrid query.

---

## Gate A — Automated tests

```text
pytest tests/test_embedding_store.py tests/test_embed_generate.py \
  tests/test_semantic_search.py tests/test_query_routing.py \
  tests/test_ollama_capability.py -q
→ 26 passed
```

| Sub-gate | Result |
|----------|--------|
| Store round-trip / self-match | PASS |
| Chunker 640/80 page-aware | PASS |
| Generate + queue (mocked) | PASS |
| Semantic API + soft-fail on embed error | PASS |
| Routing / hybrid merge | PASS |

---

## Gate B — Live stack readiness

Backend: uvicorn on `127.0.0.1:8000` against `data/index.db`. Ollama running.

| Check | Result | Observed |
|-------|--------|----------|
| `ollama.available` | PASS | `true` / `available` |
| `models.embedding` | PASS | `true` (`nomic-embed-text`) |
| `vector_store.available` + dim | PASS | sqlite-vec `v0.1.9`, dim **768** |
| `chunk_count` | PASS | **28** (matches `embedding_chunk_count`) |
| Smoke `POST /index/embeddings/smoke` | PASS | `ok`, distance **0.0** |
| GPU (informational) | OK | RTX 5060 Ti available |
| Embedded Charizard files | OK | `Charizard.pdf:6`, `Charizard.docx:1` |

Index: 67 files; embed queue depth 0; no last error.

---

## Gate C — Live search matrix

Corpus facts reconfirmed: PDF body has “pokemon” (+ species names); DOCX body is **`piplup`** only; both filenames are Charizard\*.

| ID | Query | Req mode | Resp mode | Result | Notes |
|----|-------|----------|-----------|--------|-------|
| C1 | `Charizard` | auto | classic | **PASS** | Both pdf + docx, `match=filename` |
| C2 | `pokemon` | classic | classic | **PASS** | `Charizard.pdf` content |
| C3 | `pokemon` | semantic | semantic | **PASS** | PDF **#1**, DOCX **#2** (piplup linked) |
| C4 | `pokemon` | auto | classic | **OBS** | Classic-only (1 token); PDF only — misses docx |
| C5 | `fire dragon pokemon` | semantic | semantic | **PASS** | PDF **#1** (top 5) |
| C6 | `fire dragon pokemon` | auto | semantic | **PASS** | Classic empty → semantic salvage; PDF #1 |
| C7 | `fire dragon` | semantic | semantic | **PASS** | PDF **#1**; vectors+query embed OK |
| C8 | `fire dragon` | auto | classic | **OBS** | count=0; ≤2-token skips semantic |
| C9 | `Charizard.pdf` | auto | classic | **PASS** | Filename-only; stages_skipped includes semantic |
| C10 | Ollama down | — | — | **PASS*** | Live chaos skipped; covered by `test_run_semantic_soft_fails_without_ollama` |

\*Self-match sanity: query `This it just a test for pdf parsing` (`mode=semantic`) → `Charizard.pdf` **#1**. Index and query embedder agree.

**Hard pipeline gates (C1–C3, C5–C7, C9): all green.**

---

## Gate D — Setup consistency (code vs docs)

| Check | Status |
|-------|--------|
| `DEFAULT_EMBED_MODEL = "nomic-embed-text"` (`embeddings/store.py`) | Locked OK |
| `VEC_DIMENSION = 768` (`embeddings/vec.py`) ↔ client `expected_dim` | Locked OK |
| `distance_metric=cosine` on `vec_chunks` | Locked OK |
| Query path always calls live `embed_texts` (`search/routing.py`) | **Mismatch:** [`docs/research-embeddings.md`](research-embeddings.md) claims stored-vector search works with Ollama down; code requires live query embed |
| Footer “Semantic Available” iff `embedding_chunk_count > 0` | **Mismatch:** does not require Ollama/model; can show Available while query embed would fail |
| Health `models.embedding` | True when Ollama + model tags OK; **ignores** chunk_count |
| `is_filename_like`: ≤2 short tokens → classic-only | Confirmed; drives C4/C8 observations |
| No distance threshold on k-NN results | By design; weak filler neighbors still appear after strong hits |

---

## Product gaps (follow-ups)

Status after 2026-07-28 implementation:

1. **Empty-classic escalate** — done (`*.ext` with no classic hits → semantic).
2. **Short conceptual keywords → hybrid** — done (`pokemon` / `fire dragon` classify hybrid; `*.ext` with hits stay classic-only).
3. **Distance floor** — done (`SEMANTIC_MAX_DISTANCE = 0.52`; always keep nearest).
4. **Doc fix** — done (research + architecture: query embed needs live Ollama).
5. **Ready signal** — done (`semantic_query_ready` on `/index/status`; launcher footer uses it).

---

## Conclusion

Embedding model and semantic stack are **set up correctly** and pass the audit gates. User-facing “I barely remember” gaps are **routing / readiness UX**, not a broken nomic/sqlite-vec installation.

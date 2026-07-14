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
4. Corpus is opt-in folders — never whole-disk by default. Denylist noise (node_modules, hidden junk). Indexing is background and pauseable.
5. Cap retrieved chunks. No whole-PC-in-the-prompt.
6. Post-index latency: classic search feels instant; RAG under 1 minute on this machine, aiming for seconds with a VRAM-fitting quantized model.
7. Model size is configurable / machine-tiered. Defaults fit 16GB system RAM + 8GB VRAM beside OS + app + index.
8. Same architecture on weaker/stronger machines via settings — not forks.

## Why

Avoid spending a year building something that demos well elsewhere but is unusable on the machine that matters most — and still runs (degraded) elsewhere.

## Status

Accepted
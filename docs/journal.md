# Notes

Scratchpad for decisions, open questions, and research. Prefer short dated entries.

## 2026-07-14 — Bootstrap

- Repo scaffolded with vision, folder layout, and `.gitignore`.
- Stack not locked yet (desktop shell, embedder, vector/keyword store).

## Open questions

- [ ] Desktop shell: Tauri vs Electron vs native?
- [ ] Embeddings: fully local (ONNX) vs optional cloud?
- [ ] Index store: SQLite+FTS + vectors, or dedicated engines (e.g. Tantivy / LanceDB)?
- [ ] Which file types in MVP (PDF, DOCX, Markdown, plain text, code)?
- [ ] Licensing and model distribution (download on first run vs bundle)?

## Decisions log

| Date | Decision | Why |
|------|----------|-----|
| 2026-07-14 | Local-first, hybrid search | Aligns with vision: privacy + meaning + exactness |
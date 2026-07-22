# AI Desktop Search - Project Vision

## What it is

A **local-first desktop app** (working name **MosAIq**) that turns the files on your computer into a searchable knowledge base. You ask in plain language; it finds the right documents by meaning and keyword, and surfaces answers with clear pointers back to the source files. Nothing leaves your machine unless you choose otherwise.

It is **not a chatbot**. The primary surface is a keyboard-first search launcher. Every file is a tile; together the tiles form a living mosaic of the user's digital life. Search, AI, relationships, and previews reveal portions of that mosaic without overwhelming the user. The mosaic is the **idle brand** — calm and memorable on open — then yields to results the moment the user types (Decision #004).

## Problem

Desktop search today is either brittle (filename/keyword only) or cloud-bound (upload your life to someone else's index). People lose hours hunting for "that PDF about the Q3 budget" or "the notes from the client call," even when the file is somewhere on disk. Existing OS search doesn't understand intent, and web AI tools don't see your private folders.

## Who it's for

People who live in large local file trees - knowledge workers, students, researchers, freelancers - who want fast, private answers from *their* documents without learning a query language or shipping data to the cloud.

## Product principles

1. **Local by default** - Indexing, embeddings, and retrieval run on-device. Cloud LLMs are optional and explicit.
2. **Meaning + exactness** - Semantic search for "what I meant," classic search for "what I typed." Hybrid ranking, not one or the other.
3. **Trustworthy results** - Every answer cites paths (and ideally snippets/pages) so you can open and verify the file.
4. **Stay out of the way** - Fast cold start for common queries; background indexing that doesn't thrash the machine.
5. **You control the corpus** - Choose folders, exclude noise, pause/wipe the index anytime.
6. **Capability Principle** - Always provide value regardless of available hardware. AI acceleration improves the experience but is never required for basic functionality. The system detects capabilities (API, Ollama, later GPU/models) and adapts automatically — including when Ollama is missing.

## What success looks like (MVP)

- Point the app at a set of folders (docs, notes, PDFs, common office formats).
- Ask a natural-language question and get ranked files plus a short grounded answer with citations.
- Re-index only what changed when files are added, edited, or removed.
- Work fully offline for search over an already-built index.

## Non-goals (for now)

- Replacing the full OS file manager or Finder/Explorer.
- Multi-user / team sync as a core feature.
- Becoming a general chatbot that ignores your files.
- Perfect OCR / every obscure file format on day one.

## North star

Open the app, ask the question the way you'd ask a colleague, and land on the right file in seconds - privately, on your own hardware.
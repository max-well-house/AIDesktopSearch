# SQLite index schema

Local file metadata, document body text (FTS5), and embedding chunk metadata for semantic search. Source of truth: [`backend/db/schema.py`](../backend/db/schema.py). Applied on API startup via `init_db()` (`PRAGMA user_version = 4`). The `vec_chunks` virtual table is created at runtime when sqlite-vec loads ([`backend/embeddings/vec.py`](../backend/embeddings/vec.py)).

Default path: repo `data/index.db` (gitignored). Override with `AIDESKTOP_DB`.

## Purpose

Store **opt-in folder roots**, **filename metadata**, **document body text (FTS5)**, and **chunk embeddings** so `GET /search` can find files by name/content always, and by meaning when vectors exist (Decision #006 / #007 / #008 / #54–#56 / #62 / #67).

## Privacy (VACUUM vs wipe)

| Action | What it does | What it does **not** do |
|--------|----------------|-------------------------|
| Remove folder (#40) | Deletes root + cascaded rows, then `VACUUM` (reclaim free pages) | Forensic erase of old DB pages on disk |
| **Wipe search index (#114)** | Deletes `index.db` (+ wal/shm) and recreates empty schema | Touch original user files; overwrite every freed sector |

Use wipe when you accidentally indexed something sensitive and want a clean empty index. Original documents stay on disk.

## Tables

### `roots`

One row per user-chosen corpus folder (#40).

| Column | Type | Notes |
|--------|------|--------|
| `id` | INTEGER PK | |
| `path` | TEXT NOT NULL UNIQUE | Absolute folder path |
| `added_at` | TEXT NOT NULL | ISO timestamp when the root was first added |
| `last_scan_at` | TEXT | ISO timestamp of the latest successful scan of this root |
| `auto_watch` | INTEGER NOT NULL DEFAULT 1 | `#118` — `1` live watch, `0` Rescan-only |

Deleting a root cascades to its `files` rows (and `file_content` / `embedding_chunks` via FK), then the API runs `VACUUM` (light reclaim — not a forensic wipe; see #114). FTS and vec rows are cleared by DELETE triggers.

### `files`

One row per indexed file under a root (#41 / #42).

| Column | Type | Notes |
|--------|------|--------|
| `id` | INTEGER PK | |
| `root_id` | INTEGER | FK → `roots(id)` **ON DELETE CASCADE** |
| `path` | TEXT NOT NULL UNIQUE | Absolute file path |
| `name` | TEXT NOT NULL | Basename (search target for classic `LIKE`) |
| `extension` | TEXT | Lowercase **without** leading `.` (e.g. `pdf`); may be null |
| `size` | INTEGER | Bytes; may be null |
| `mtime` | REAL | Filesystem mtime; may be null |
| `indexed_at` | TEXT NOT NULL | ISO timestamp when this row was last written |

### `file_content` (#55 / #62)

One row per parsed content-eligible file (Decision #006 / #007). PDF first; TXT / MD / DOCX register via `CONTENT_EXTENSIONS`.

| Column | Type | Notes |
|--------|------|--------|
| `file_id` | INTEGER PK | FK → `files(id)` **ON DELETE CASCADE** |
| `parser` | TEXT NOT NULL | e.g. `pymupdf` |
| `parser_version` | TEXT | Library version string when known |
| `page_count` | INTEGER | Pages/segments seen at parse time |
| `mtime_at_parse` | REAL | Skip re-parse when equal to `files.mtime` |
| `status` | TEXT NOT NULL | `ok` \| `empty` \| `error` |
| `warning` | TEXT | Soft-fail / cap reason |
| `parsed_at` | TEXT NOT NULL | ISO timestamp |

### `file_pages_fts` (#55 / #62)

FTS5 virtual table: `text`, `file_id UNINDEXED`, `page UNINDEXED` (1-based). One row per page/segment with extractable text. PDFs use real page numbers; linear formats use a single segment at `page=1` (launcher shows “Page N” only for PDFs).

Trigger `files_ad_pages_fts`: after DELETE on `files`, remove matching FTS rows (FTS does not cascade).

### `embedding_chunks` (#67)

Chunk metadata for meaning search. Vectors live in `vec_chunks` (sqlite-vec).

| Column | Type | Notes |
|--------|------|--------|
| `id` | INTEGER PK | Shared with `vec_chunks.chunk_id` |
| `file_id` | INTEGER NOT NULL | FK → `files(id)` **ON DELETE CASCADE** |
| `page` | INTEGER | Page when known (PDF); may be null |
| `chunk_index` | INTEGER NOT NULL | Order within the file |
| `text_preview` | TEXT | Short snippet for debugging / future UI |
| `model_id` | TEXT NOT NULL | e.g. `nomic-embed-text` — do not mix models without re-embed |
| `dim` | INTEGER NOT NULL | Must match locked vec0 dim (768 for v0.7) |
| `content_hash` | TEXT | Optional fingerprint for skip/re-embed |
| `created_at` | TEXT NOT NULL | ISO timestamp |

Unique `(file_id, chunk_index, model_id)`.

### `vec_chunks` (#67)

sqlite-vec `vec0` virtual table created when the extension loads:

- `chunk_id INTEGER PRIMARY KEY`
- `embedding float[768] distance_metric=cosine`

Missing extension → classic search still works; no vec table; store APIs soft-fail (Decision #008).

Trigger `embedding_chunks_ad_vec`: after DELETE on `embedding_chunks`, remove the matching `vec_chunks` row.

## Indexes

| Name | Definition | Why |
|------|------------|-----|
| `idx_files_name` | `files(name COLLATE NOCASE)` | Case-insensitive filename search |
| `idx_files_root_id` | `files(root_id)` | Fast delete/rescan per root |
| `idx_embedding_chunks_file_id` | `embedding_chunks(file_id)` | Clear/re-embed per file |
| `idx_embedding_chunks_model` | `embedding_chunks(model_id)` | Filter by embedding model |

## Status fields (API, not columns)

`GET /index/status` derives:

- `file_count` / `root_count` — row counts
- `last_indexed_at` — `MAX(files.indexed_at)` (feeds Footer **Indexed** date, #115)
- Per-root `file_count` and `last_scan_at` — System Status only
- Live watching (#48–#52): `watching`, `watched_roots`, `queue_depth`, `watch_paused` (from the in-process watcher — not DB columns)
- Embedding store (#67): `embedding_chunk_count`, `vector_store_available`

`GET /health` → `capabilities.vector_store` (`available`, `version`, `note`, `dimension`, `chunk_count`).

`POST /index/embeddings/smoke` — throwaway round-trip for System Status **Verify vector store** (needs ≥1 indexed file; leaves no smoke rows).

## Incremental updates (v0.4+)

Create / replace / delete / rename under a watched root update `files` rows via `upsert_file` / `delete_file` / `rename_file` (and prefix helpers for directory moves). Content-eligible create/modify also syncs `file_content` + FTS when `extension` is in `CONTENT_EXTENSIONS`. Clearing content also clears embedding chunks for that file. Cold start reconciles with a full rescan per root before watching resumes. Embedding *generation* on change is #66.

## Explicitly not in schema (yet)

Watcher cursors. Generate pipeline (#66), semantic query endpoint (#68), hybrid ranking (#69).

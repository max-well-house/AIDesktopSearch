# SQLite index schema

Local file metadata and PDF content for classic search. Source of truth: [`backend/db/schema.py`](../backend/db/schema.py). Applied on API startup via `init_db()` (`PRAGMA user_version = 2`).

Default path: repo `data/index.db` (gitignored). Override with `AIDESKTOP_DB`.

## Purpose

Store **opt-in folder roots**, **filename metadata**, and **document body text (FTS5)** so `GET /search` can find files by name or content without Ollama (Decision #006 / #007 / #54–#56 / #62).

## Tables

### `roots`

One row per user-chosen corpus folder (#40).

| Column | Type | Notes |
|--------|------|--------|
| `id` | INTEGER PK | |
| `path` | TEXT NOT NULL UNIQUE | Absolute folder path |
| `added_at` | TEXT NOT NULL | ISO timestamp when the root was first added |
| `last_scan_at` | TEXT | ISO timestamp of the latest successful scan of this root |

Deleting a root cascades to its `files` rows (and `file_content` via FK), then the API runs `VACUUM` (light reclaim — not a forensic wipe; see #114). FTS rows are cleared by the `files` DELETE trigger.

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

## Indexes

| Name | Definition | Why |
|------|------------|-----|
| `idx_files_name` | `files(name COLLATE NOCASE)` | Case-insensitive filename search |
| `idx_files_root_id` | `files(root_id)` | Fast delete/rescan per root |

## Status fields (API, not columns)

`GET /index/status` derives:

- `file_count` / `root_count` — row counts
- `last_indexed_at` — `MAX(files.indexed_at)` (feeds Footer **Indexed** date, #115)
- Per-root `file_count` and `last_scan_at` — System Status only
- Live watching (#48–#52): `watching`, `watched_roots`, `queue_depth`, `watch_paused` (from the in-process watcher — not DB columns)

## Incremental updates (v0.4+)

Create / replace / delete / rename under a watched root update `files` rows via `upsert_file` / `delete_file` / `rename_file` (and prefix helpers for directory moves). Content-eligible create/modify also syncs `file_content` + FTS when `extension` is in `CONTENT_EXTENSIONS` (PDF in v0.5; more formats in v0.6). Cold start reconciles with a full rescan per root before watching resumes.

## Explicitly not in schema (yet)

Chunks, embeddings, watcher cursors. Document body text for non-PDF formats reuses `file_content` / `file_pages_fts` (Decision #007) — no new tables for v0.6. Add tables when #67 (sqlite-vec / Decision #008) needs them; bump `user_version` in `schema.py`. Conceptual pipeline: [research-embeddings.md](./research-embeddings.md) (#63); store choice: [research-vector-databases.md](./research-vector-databases.md) (#64).

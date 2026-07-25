# SQLite index schema

Local file metadata for classic search. Source of truth: [`backend/db/schema.py`](../backend/db/schema.py). Applied on API startup via `init_db()` (`PRAGMA user_version = 1`).

Default path: repo `data/index.db` (gitignored). Override with `AIDESKTOP_DB`.

## Purpose

Store **opt-in folder roots** and **filename metadata** so `GET /search` can find files without Ollama. No content, embeddings, or FTS tables yet (those arrive in later milestones).

## Tables

### `roots`

One row per user-chosen corpus folder (#40).

| Column | Type | Notes |
|--------|------|--------|
| `id` | INTEGER PK | |
| `path` | TEXT NOT NULL UNIQUE | Absolute folder path |
| `added_at` | TEXT NOT NULL | ISO timestamp when the root was first added |
| `last_scan_at` | TEXT | ISO timestamp of the latest successful scan of this root |

Deleting a root cascades to its `files` rows, then the API runs `VACUUM` (light reclaim — not a forensic wipe; see #114).

### `files`

One row per indexed file under a root (#41 / #42).

| Column | Type | Notes |
|--------|------|--------|
| `id` | INTEGER PK | |
| `root_id` | INTEGER | FK → `roots(id)` **ON DELETE CASCADE** |
| `path` | TEXT NOT NULL UNIQUE | Absolute file path |
| `name` | TEXT NOT NULL | Basename (search target for classic `LIKE`) |
| `extension` | TEXT | Including leading `.` when present; may be null |
| `size` | INTEGER | Bytes; may be null |
| `mtime` | REAL | Filesystem mtime; may be null |
| `indexed_at` | TEXT NOT NULL | ISO timestamp when this row was last written |

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

## Incremental updates (v0.4)

Create / modify / delete / rename under a watched root update `files` rows via `upsert_file` / `delete_file` / `rename_file` (and prefix helpers for directory moves). No watcher cursor tables — events are applied live; cold start reconciles with a full rescan per root before watching resumes.

## Explicitly not in schema (yet)

Content blobs, chunks, embeddings, FTS, watcher cursors. Add tables when those milestones need them; bump `user_version` in `schema.py`.

PDF / document **content + FTS** arrive with #55 (Decision #006 — PyMuPDF extract in #54 first). Still no content columns in `user_version = 1`.

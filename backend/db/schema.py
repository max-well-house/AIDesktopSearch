"""SQLite schema for file metadata + PDF content FTS (#39 / #54–#55).

Human write-up: docs/schema.md (#47).
"""

SCHEMA_VERSION = 2

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS roots (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    added_at TEXT NOT NULL,
    last_scan_at TEXT
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    root_id INTEGER REFERENCES roots(id) ON DELETE CASCADE,
    path TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    extension TEXT,
    size INTEGER,
    mtime REAL,
    indexed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_files_name ON files(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_files_root_id ON files(root_id);

CREATE TABLE IF NOT EXISTS file_content (
    file_id INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
    parser TEXT NOT NULL,
    parser_version TEXT,
    page_count INTEGER,
    mtime_at_parse REAL,
    status TEXT NOT NULL,
    warning TEXT,
    parsed_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS file_pages_fts USING fts5(
    text,
    file_id UNINDEXED,
    page UNINDEXED
);

CREATE TRIGGER IF NOT EXISTS files_ad_pages_fts
AFTER DELETE ON files
BEGIN
    DELETE FROM file_pages_fts WHERE file_id = old.id;
END;
"""

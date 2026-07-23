"""SQLite schema foundation for file metadata (#39).

Keep this minimal: enough for #41 (save metadata) and #42 (filename search)
without inventing content/embedding tables yet. Full write-up lives in #47.
"""

SCHEMA_VERSION = 1

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
"""

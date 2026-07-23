"""Walk a user-selected folder and collect file paths for indexing (#41).

Full opt-in folder UX is #40; ignore-rule polish is #45/#46.
A small denylist here avoids accidental huge scans while testing.
"""

from __future__ import annotations

import os
from pathlib import Path

# Minimal noise skip — expanded properly in #45/#46.
_SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "dist",
    "build",
    ".next",
    ".turbo",
}


def iter_files(root: Path) -> list[Path]:
    """Return files under root (recursive). Raises if missing / not a folder."""
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Folder not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Not a folder: {root}")

    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in _SKIP_DIR_NAMES and not d.startswith(".")
        ]
        for name in filenames:
            # Skip dotfiles at the file level for now (#45).
            if name.startswith("."):
                continue
            found.append(Path(dirpath) / name)
    return found

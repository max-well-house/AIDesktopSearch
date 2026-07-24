"""Walk a user-selected folder and collect file paths for indexing (#41).

Ignore rules live in ``indexer.ignore`` (#45 hidden folders, #46 denylist).
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from indexer.ignore import should_skip_dir, should_skip_file


def iter_files(
    root: Path,
    *,
    extra_skip_dirs: Iterable[str] | None = None,
    skip_hidden: bool = True,
) -> list[Path]:
    """Return files under root (recursive). Raises if missing / not a folder.

    By default skips dot-prefixed (hidden) names and ``DEFAULT_SKIP_DIR_NAMES``
    (includes ``node_modules``). Pass ``extra_skip_dirs`` to extend the denylist
    for one scan without changing defaults.
    """
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
            if not should_skip_dir(
                d,
                extra_skip_dirs=extra_skip_dirs,
                skip_hidden=skip_hidden,
            )
        ]
        for name in filenames:
            if should_skip_file(name, skip_hidden=skip_hidden):
                continue
            found.append(Path(dirpath) / name)
    return found

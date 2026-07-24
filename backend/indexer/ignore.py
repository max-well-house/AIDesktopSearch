"""Shared scan/watch ignore rules (#45 hidden, #46 denylist).

Keep this module the single source of truth so a future watchdog path
reuses the same filters (Decision #005 / research-filesystem-watchers.md).
"""

from __future__ import annotations

from collections.abc import Iterable

# Exact directory basenames pruned from walks. Add names here to extend.
DEFAULT_SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
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
)


def is_hidden_name(name: str) -> bool:
    """True for dot-prefixed names (hidden by convention on Unix / cross-platform).

    Does not check Windows FILE_ATTRIBUTE_HIDDEN; that can land later if needed.
    """
    return bool(name) and name.startswith(".")


def should_skip_dir(
    name: str,
    *,
    skip_dirs: frozenset[str] | None = None,
    extra_skip_dirs: Iterable[str] | None = None,
    skip_hidden: bool = True,
) -> bool:
    """Whether a child directory basename should be pruned from the walk."""
    names = skip_dirs if skip_dirs is not None else DEFAULT_SKIP_DIR_NAMES
    if extra_skip_dirs:
        names = names | frozenset(extra_skip_dirs)
    if name in names:
        return True
    if skip_hidden and is_hidden_name(name):
        return True
    return False


def should_skip_file(name: str, *, skip_hidden: bool = True) -> bool:
    """Whether a file basename should be omitted from the index."""
    return skip_hidden and is_hidden_name(name)

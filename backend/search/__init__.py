"""Query routing and search orchestration (Decision #002 / #98)."""

from search.routing import (
    SearchMode,
    classify_query,
    execute_search,
    is_filename_like,
    merge_hybrid_results,
    run_classic,
    run_llm,
    run_semantic,
)

__all__ = [
    "SearchMode",
    "classify_query",
    "execute_search",
    "is_filename_like",
    "merge_hybrid_results",
    "run_classic",
    "run_llm",
    "run_semantic",
]

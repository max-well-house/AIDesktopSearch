#!/usr/bin/env python3
"""Assert Meshen search hits match corpus expected_search (#140).

Requires:
  1. ``python tools/corpus/generate.py`` (or an existing corpus + manifest)
  2. Meshen backend running with that corpus folder as an index root
  3. For ``mode: semantic`` entries: embeddings ready (Ollama + nomic-embed-text)

Usage (from repo root):
  python tools/corpus/eval_search.py
  python tools/corpus/eval_search.py --manifest %USERPROFILE%\\Documents\\Meshen-TestCorpus\\manifest.json
  python tools/corpus/eval_search.py --modes classic   # skip semantic
  python tools/corpus/eval_search.py --include-rag     # also run expected_rag (needs #71)
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_CORPUS_DIRNAME = "Meshen-TestCorpus"
MANIFEST_NAME = "manifest.json"


def _default_manifest() -> Path:
    documents = Path.home() / "Documents"
    root = documents / DEFAULT_CORPUS_DIRNAME if documents.is_dir() else Path.home() / DEFAULT_CORPUS_DIRNAME
    return root / MANIFEST_NAME


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_expectation(raw) -> dict | None:
    """Accept legacy list form or structured {must_include, ...}."""
    if raw is None:
        return None
    if isinstance(raw, list):
        return {"must_include": list(raw), "mode": "classic"}
    if isinstance(raw, dict):
        return raw
    return None


def _hit_paths(payload: dict) -> list[str]:
    results = payload.get("results") or []
    paths: list[str] = []
    for hit in results:
        if isinstance(hit, dict) and hit.get("path"):
            paths.append(str(hit["path"]).replace("\\", "/"))
    return paths


def _matches_rel(abs_path: str, rel: str, corpus_root: Path) -> bool:
    rel_n = rel.replace("\\", "/")
    abs_n = abs_path.replace("\\", "/")
    if abs_n.endswith("/" + rel_n) or abs_n.endswith(rel_n):
        return True
    try:
        expected = (corpus_root / rel_n).resolve()
        return Path(abs_path).resolve() == expected
    except OSError:
        return False


def _search(base_url: str, query: str, *, mode: str, limit: int) -> dict:
    params = urllib.parse.urlencode({"q": query, "mode": mode, "limit": limit})
    url = f"{base_url.rstrip('/')}/search?{params}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _status(base_url: str) -> dict:
    url = f"{base_url.rstrip('/')}/index/status"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _evaluate_entry(
    query: str,
    expectation: dict,
    *,
    base_url: str,
    corpus_root: Path,
    default_mode: str,
) -> tuple[bool, str]:
    mode = (expectation.get("mode") or default_mode).strip().lower()
    # Map rag → auto until a dedicated ask path exists; still checks retrieval hits.
    search_mode = "auto" if mode in {"rag", "semantic", "hybrid", "auto"} else "classic"
    if mode == "classic":
        search_mode = "classic"

    must_include = list(expectation.get("must_include") or [])
    must_exclude = list(expectation.get("must_exclude") or [])
    top_k = expectation.get("top_k")
    limit = int(top_k) if isinstance(top_k, int) and top_k > 0 else max(20, len(must_include) + 5)

    try:
        payload = _search(base_url, query, mode=search_mode, limit=limit)
    except urllib.error.URLError as exc:
        return False, f"request failed: {exc}"
    except Exception as exc:  # noqa: BLE001
        return False, f"error: {exc}"

    paths = _hit_paths(payload)
    missing = [
        rel
        for rel in must_include
        if not any(_matches_rel(p, rel, corpus_root) for p in paths)
    ]
    extras = [
        rel
        for rel in must_exclude
        if any(_matches_rel(p, rel, corpus_root) for p in paths)
    ]
    if missing or extras:
        detail = []
        if missing:
            detail.append(f"missing {missing}")
        if extras:
            detail.append(f"unexpected {extras}")
        return False, "; ".join(detail) + f" (got {len(paths)} hits, mode={payload.get('mode')})"
    return True, f"ok ({len(paths)} hits, mode={payload.get('mode')})"


def run(
    *,
    manifest_path: Path,
    base_url: str,
    modes: set[str],
    include_rag: bool,
) -> int:
    try:
        manifest = _load_manifest(manifest_path)
    except OSError as exc:
        print(f"error: cannot read manifest: {exc}", file=sys.stderr)
        return 2

    corpus_root = Path(manifest.get("root") or manifest_path.parent).resolve()
    try:
        status = _status(base_url)
    except urllib.error.URLError as exc:
        print(f"error: backend unreachable at {base_url}: {exc}", file=sys.stderr)
        print("Start Meshen (or uvicorn) and add the corpus folder as an index root.", file=sys.stderr)
        return 2

    semantic_ready = bool(status.get("semantic_query_ready"))
    print(f"Manifest: {manifest_path}")
    print(f"Corpus root: {corpus_root}")
    print(f"Backend: {base_url} (semantic_query_ready={semantic_ready})")

    failures = 0
    skipped = 0
    checked = 0

    entries: list[tuple[str, dict, str]] = []
    for query, raw in (manifest.get("expected_search") or {}).items():
        exp = _normalize_expectation(raw)
        if exp is None:
            continue
        entries.append((query, exp, "search"))

    if include_rag:
        for query, raw in (manifest.get("expected_rag") or {}).items():
            exp = _normalize_expectation(raw)
            if exp is None:
                continue
            entries.append((query, exp, "rag"))

    for query, exp, kind in entries:
        mode = (exp.get("mode") or "classic").strip().lower()
        if mode not in modes and not (include_rag and kind == "rag" and mode == "rag"):
            if mode == "rag" and not include_rag:
                skipped += 1
                print(f"SKIP  [{mode}] {query!r} (pass --include-rag after #71)")
                continue
            if mode not in modes:
                skipped += 1
                print(f"SKIP  [{mode}] {query!r}")
                continue

        if mode == "semantic" and not semantic_ready:
            skipped += 1
            print(f"SKIP  [semantic] {query!r} (semantic_query_ready=false)")
            continue

        if mode == "rag" and not include_rag:
            skipped += 1
            print(f"SKIP  [rag] {query!r}")
            continue

        ok, msg = _evaluate_entry(
            query,
            exp,
            base_url=base_url,
            corpus_root=corpus_root,
            default_mode=mode,
        )
        checked += 1
        label = "PASS" if ok else "FAIL"
        print(f"{label}  [{mode}] {query!r}: {msg}")
        if not ok:
            failures += 1

    print(f"\nChecked {checked}, skipped {skipped}, failed {failures}")
    return 1 if failures else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Eval Meshen search against corpus expected hits.")
    p.add_argument(
        "--manifest",
        type=Path,
        default=_default_manifest(),
        help=f"Path to manifest.json (default: {_default_manifest()})",
    )
    p.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Meshen API base URL (default: {DEFAULT_BASE_URL})",
    )
    p.add_argument(
        "--modes",
        default="classic,semantic",
        help="Comma-separated modes to run (default: classic,semantic)",
    )
    p.add_argument(
        "--include-rag",
        action="store_true",
        help="Also evaluate expected_rag (after RAG/citations ship)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    modes = {m.strip().lower() for m in args.modes.split(",") if m.strip()}
    if args.include_rag:
        modes.add("rag")
    return run(
        manifest_path=args.manifest,
        base_url=args.base_url,
        modes=modes,
        include_rag=args.include_rag,
    )


if __name__ == "__main__":
    raise SystemExit(main())

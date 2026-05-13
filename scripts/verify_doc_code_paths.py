#!/usr/bin/env python3
"""Verify backtick-wrapped repo paths in markdown point at existing files.

Scans selected trees for inline `` `path/to/file.py` `` segments that look like
repository-relative paths and fails if any target is missing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Markdown trees called out in the evaluation-gap plan (repo-root-relative `.py` only).
SCAN_PATHS: tuple[Path, ...] = (
    ROOT / "README.md",
    ROOT / "ARCHITECTURE.md",
    ROOT / "reports",
    ROOT / "module_a_population_segmentation" / "reports",
)

# Only resolve paths that are unambiguously anchored at the repository root.
_REPO_PATH_PREFIXES: tuple[str, ...] = (
    "module_a_population_segmentation/",
    "module_b_resource_allocation/",
    "module_c_forecasting_scenarios/",
    "scripts/",
    "tests/",
    "schema_contracts/",
    ".github/",
)

INLINE_CODE = re.compile(r"`([^`]+)`")


def _iter_markdown_files() -> list[Path]:
    out: list[Path] = []
    for p in SCAN_PATHS:
        if p.is_file() and p.suffix == ".md":
            out.append(p)
        elif p.is_dir():
            out.extend(sorted(p.rglob("*.md")))
    return out


def _looks_like_repo_py_path(s: str) -> bool:
    t = s.strip()
    if not t or "\n" in t or " " in t or len(t) > 400:
        return False
    if t.startswith(("http://", "https://", "mailto:", "#")):
        return False
    if "/" not in t:
        return False
    if ".." in t.split("/"):
        return False
    if "{" in t or "}" in t:
        return False
    if not t.endswith(".py"):
        return False
    if any(c in t for c in ("<", ">", "*", "${")):
        return False
    return any(t.startswith(p) for p in _REPO_PATH_PREFIXES)


def _resolve_under_root(rel: str) -> Path:
    candidate = (ROOT / rel).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError as e:
        raise ValueError(f"path escapes repo root: {rel!r}") from e
    return candidate


def main() -> int:
    missing: list[str] = []
    scanned = 0
    checked = 0
    for md in _iter_markdown_files():
        if "pre_public_cleanup" in str(md) or "ai_harness" in str(md):
            continue
        scanned += 1
        text = md.read_text(encoding="utf-8", errors="replace")
        for m in INLINE_CODE.finditer(text):
            raw = m.group(1).strip()
            if not _looks_like_repo_py_path(raw):
                continue
            checked += 1
            try:
                path = _resolve_under_root(raw)
            except ValueError as e:
                missing.append(f"{md.relative_to(ROOT)}: {e}")
                continue
            if not path.is_file():
                missing.append(f"{md.relative_to(ROOT)}: missing {raw}")

    if missing:
        print("verify_doc_code_paths FAILED:\n" + "\n".join(missing))
        return 1
    print(f"verify_doc_code_paths OK ({scanned} markdown files, {checked} path-like inline codes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

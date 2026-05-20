#!/usr/bin/env python3
"""Overwrite / insert YAML frontmatter from docs_registry.yaml (does not alter markdown body)."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_YAML = ROOT / "docs" / "registry" / "docs_registry.yaml"
TAX_PATH = ROOT / "docs" / "registry" / "taxonomy.yaml"
TAX = yaml.safe_load(TAX_PATH.read_text(encoding="utf-8"))

FRONTMATTER_BLOCK = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)


def load_documents() -> list[dict[str, Any]]:
    reg = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    return cast(list[dict[str, Any]], reg["documents"])


def norm_list_maybe_null(val: object) -> Any:
    if val is None:
        return None
    if isinstance(val, list) and len(val) == 0:
        return None
    return val


def build_frontmatter_dict(entry: dict[str, Any]) -> dict[str, Any]:
    fm: dict[str, Any] = {
        "doc_id": entry["doc_id"],
        "doc_type": entry["doc_type"],
        "doc_role": entry["doc_role"],
        "visibility": entry["visibility"],
        "status": entry.get("status", "active"),
        "owner": entry["owner"],
        "last_reviewed": entry["last_reviewed"],
    }
    fm["canonical_source"] = norm_list_maybe_null(entry.get("canonical_source"))
    fm["derived_from"] = norm_list_maybe_null(entry.get("derived_from"))
    fm["supersedes"] = norm_list_maybe_null(entry.get("supersedes"))
    tags = entry.get("tags") or []
    fm["tags"] = tags if isinstance(tags, list) else [str(tags)]

    if entry.get("allowed_content"):
        fm["allowed_content"] = entry["allowed_content"]
    if entry.get("forbidden_content"):
        fm["forbidden_content"] = entry["forbidden_content"]
    return fm


def dump_fm(fm: dict[str, Any]) -> str:
    text = yaml.safe_dump(
        fm,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=160,
    ).strip()
    return f"---\n{text}\n---\n\n"


def main() -> int:
    for entry in load_documents():
        if not entry.get("frontmatter_required", True):
            continue
        path = ROOT / str(entry["path"])
        body = path.read_text(encoding="utf-8", errors="replace")
        stripped = FRONTMATTER_BLOCK.sub("", body).lstrip()
        fm_yaml = dump_fm(build_frontmatter_dict(entry))
        path.write_text(fm_yaml + stripped, encoding="utf-8")
        print(f"synced frontmatter → {entry['path']}")
    print("sync_doc_frontmatter OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

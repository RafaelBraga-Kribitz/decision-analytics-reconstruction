#!/usr/bin/env python3
"""YAML frontmatter in tracked docs must mirror docs_registry.yaml."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_YAML = ROOT / "docs" / "registry" / "docs_registry.yaml"
TAX_YAML = ROOT / "docs" / "registry" / "taxonomy.yaml"

FRONTMATTER_BLOCK = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def load_registry_documents() -> list[dict[str, Any]]:
    reg = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    return cast(list[dict[str, Any]], reg["documents"])


def extract_frontmatter(path: Path) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = FRONTMATTER_BLOCK.match(text)
    if not m:
        return None
    return yaml.safe_load(m.group(1))


def fm_equal(a: object, b: object) -> bool:
    """Loose equality (ignore ordering for small lists shown in YAML differently)."""
    if type(a) is not type(b) and not (isinstance(a, list) and isinstance(b, list)):
        return False
    if isinstance(a, list) and isinstance(b, list):
        return sorted(str(x) for x in a) == sorted(str(x) for x in b)
    return a == b


def _required_field_problems(
    path: str,
    fm: dict[str, Any],
    required_fields: list[str],
) -> list[str]:
    problems: list[str] = []
    for field in required_fields:
        if field not in fm or fm[field] is None:
            problems.append(f"{path}: frontmatter missing required field {field!r}")
    return problems


def _identity_field_problems(path: str, fm: dict[str, Any], d: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    did = str(fm.get("doc_id", ""))
    if did != str(d["doc_id"]):
        problems.append(f"{path}: frontmatter doc_id {did!r} != registry {d['doc_id']!r}")
    for key in ("doc_type", "doc_role", "visibility", "status", "owner"):
        if key in d and key in fm and not fm_equal(fm[key], d[key]):
            problems.append(
                f"{path}: frontmatter {key} {fm[key]!r} != registry {d[key]!r}",
            )
    return problems


def _derived_canonical_problems(path: str, fm: dict[str, Any], d: dict[str, Any]) -> list[str]:
    if d.get("doc_role") != "derived":
        return []
    reg_canon = d.get("canonical_source") or []
    fm_canon = fm.get("canonical_source")
    if not reg_canon:
        return [f"{path}: registry derived doc missing canonical_source"]
    if fm_canon is None:
        return [f"{path}: derived doc frontmatter must set canonical_source list"]
    if sorted(str(x) for x in fm_canon) != sorted(str(x) for x in reg_canon):
        return [
            f"{path}: frontmatter canonical_source mismatch vs registry "
            f"{reg_canon!r} vs {fm_canon!r}",
        ]
    return []


def _validate_document(
    d: dict[str, Any],
    required_fields: list[str],
) -> list[str]:
    path = str(d["path"])
    if not d.get("frontmatter_required", True):
        return []
    fm = extract_frontmatter(ROOT / path)
    if fm is None:
        return [f"{path}: missing YAML frontmatter block"]
    problems: list[str] = []
    problems.extend(_required_field_problems(path, fm, required_fields))
    problems.extend(_identity_field_problems(path, fm, d))
    problems.extend(_derived_canonical_problems(path, fm, d))
    return problems


def main() -> int:
    tax = yaml.safe_load(TAX_YAML.read_text(encoding="utf-8"))
    required_fields = cast(list[str], tax["frontmatter_required_fields"])
    problems: list[str] = []
    for d in load_registry_documents():
        problems.extend(_validate_document(d, required_fields))

    if problems:
        print("check_doc_frontmatter FAILED:\n" + "\n".join(problems[:200]))
        return 1
    print("check_doc_frontmatter OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

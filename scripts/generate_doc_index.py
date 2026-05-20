#!/usr/bin/env python3
"""Generate docs/INDEX.md from docs/registry/docs_registry.yaml (machine-readable SSOT view)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_YAML = ROOT / "docs" / "registry" / "docs_registry.yaml"
INDEX_MD = ROOT / "docs" / "INDEX.md"


def load_registry() -> list[dict[str, Any]]:
    reg = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    return cast(list[dict[str, Any]], reg["documents"])


def render_index(documents: list[dict[str, Any]]) -> str:
    lines: list[str] = [
        "---",
        "doc_id: DOC-REG-INDEX",
        "doc_type: registry",
        "doc_role: registry",
        "visibility: public",
        "status: generated",
        "owner: architecture",
        'last_reviewed: "2026-05-20"',
        "canonical_source: null",
        "derived_from: []",
        "supersedes: []",
        "tags:",
        "  - generated",
        "---",
        "",
        "# Documentation index",
        "",
        "_This file is generated from `docs/registry/docs_registry.yaml`. Do not edit by hand._",
        "",
        "Run `poetry run python scripts/generate_doc_index.py --write` after registry changes.",
        "",
        "## Retrieval order (agents)",
        "",
        "1. `docs/registry/docs_registry.yaml`",
        "2. Canonical docs (`authority: canonical`)",
        "3. Derived views",
        "4. Evidence (`maintainer/evidence/`)",
        "5. Archived lineage only",
        "",
        "## Canonically authoritative (selection)",
        "",
    ]
    canon = [
        d
        for d in documents
        if d.get("authority") == "canonical" and str(d.get("status")) == "active"
    ]
    canon.sort(key=lambda d: str(d["path"]))
    for d in canon:
        dt, dr = d.get("doc_type"), d.get("doc_role")
        lines.append(
            f"- **{d['doc_id']}** — `{d['path']}` — *{dt}* / *{dr}*",
        )
    lines.append("")
    lines.append("## Derived portfolio views")
    lines.append("")
    derived = [
        d for d in documents if d.get("doc_role") == "derived" and str(d.get("status")) == "active"
    ]
    derived.sort(key=lambda d: str(d["path"]))
    for d in derived:
        src = ", ".join(str(x) for x in (d.get("canonical_source") or []))
        lines.append(f"- **{d['doc_id']}** — `{d['path']}` — canonical: {src or '—'}")
    lines.append("")
    lines.append("## Evidence and internal artifacts")
    lines.append("")
    evid = [
        d for d in documents if d.get("doc_type") == "evidence" or d.get("authority") == "evidence"
    ]
    evid.sort(key=lambda d: str(d["path"]))
    for d in evid[:60]:
        lines.append(f"- **{d['doc_id']}** — `{d['path']}` — *{d.get('status')}*")
    if len(evid) > 60:
        lines.append(f"- … and {len(evid) - 60} more evidence rows (see YAML registry)")
    lines.append("")
    lines.append("## Research inputs (reference only)")
    lines.append("")
    res = [d for d in documents if d.get("doc_type") == "research"]
    res.sort(key=lambda d: str(d["path"]))
    for d in res:
        lines.append(f"- **{d['doc_id']}** — `{d['path']}`")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="Write docs/INDEX.md")
    ap.add_argument(
        "--check",
        action="store_true",
        help="Fail if INDEX.md differs from generator output",
    )
    args = ap.parse_args()

    body = render_index(load_registry())
    if args.write:
        INDEX_MD.write_text(body, encoding="utf-8")
        print(f"Wrote {INDEX_MD}")
        return 0
    if args.check:
        if not INDEX_MD.is_file():
            print(f"generate_doc_index --check FAILED: missing {INDEX_MD}")
            return 1
        cur = INDEX_MD.read_text(encoding="utf-8")
        if cur != body:
            print(
                "generate_doc_index --check FAILED: docs/INDEX.md out of date — run\n"
                "  poetry run python scripts/generate_doc_index.py --write"
            )
            return 1
        print("generate_doc_index --check OK")
        return 0

    # default: print diff hint
    print("Specify --write or --check")
    return 1


if __name__ == "__main__":
    sys.exit(main())

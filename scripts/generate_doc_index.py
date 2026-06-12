#!/usr/bin/env python3
"""Generate docs/INDEX.md from docs/registry/docs_registry.yaml (machine-readable SSOT view)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_YAML = ROOT / "docs" / "registry" / "docs_registry.yaml"
INDEX_MD = ROOT / "docs" / "INDEX.md"


def load_registry() -> list[dict[str, Any]]:
    reg = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    return cast(list[dict[str, Any]], reg["documents"])


def _index_header_lines() -> list[str]:
    return [
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
    ]


def _render_section(
    lines: list[str],
    title: str,
    documents: list[dict[str, Any]],
    formatter: Callable[[dict[str, Any]], str],
    *,
    limit: int | None = None,
    overflow_msg: str | None = None,
) -> None:
    lines.append(title)
    lines.append("")
    subset = documents[:limit] if limit else documents
    for d in subset:
        lines.append(formatter(d))
    if limit and len(documents) > limit and overflow_msg:
        lines.append(overflow_msg.format(extra=len(documents) - limit))
    lines.append("")


def _sorted_docs(
    documents: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
) -> list[dict[str, Any]]:
    return sorted([d for d in documents if predicate(d)], key=lambda d: str(d["path"]))


def _format_canonical(d: dict[str, Any]) -> str:
    return (
        f"- **{d['doc_id']}** — `{d['path']}` — " f"*{d.get('doc_type')}* / *{d.get('doc_role')}*"
    )


def _format_derived(d: dict[str, Any]) -> str:
    src = ", ".join(str(x) for x in (d.get("canonical_source") or [])) or "—"
    return f"- **{d['doc_id']}** — `{d['path']}` — canonical: {src}"


def _format_evidence(d: dict[str, Any]) -> str:
    return f"- **{d['doc_id']}** — `{d['path']}` — *{d.get('status')}*"


def _format_research(d: dict[str, Any]) -> str:
    return f"- **{d['doc_id']}** — `{d['path']}`"


def render_index(documents: list[dict[str, Any]]) -> str:
    lines = _index_header_lines()

    _render_section(
        lines,
        "## Canonically authoritative (selection)",
        _sorted_docs(
            documents,
            lambda d: d.get("authority") == "canonical" and str(d.get("status")) == "active",
        ),
        _format_canonical,
    )

    _render_section(
        lines,
        "## Derived portfolio views",
        _sorted_docs(
            documents,
            lambda d: d.get("doc_role") == "derived" and str(d.get("status")) == "active",
        ),
        _format_derived,
    )

    _render_section(
        lines,
        "## Evidence and internal artifacts",
        _sorted_docs(
            documents,
            lambda d: d.get("doc_type") == "evidence" or d.get("authority") == "evidence",
        ),
        _format_evidence,
        limit=60,
        overflow_msg="- … and {extra} more evidence rows (see YAML registry)",
    )

    _render_section(
        lines,
        "## Research inputs (reference only)",
        _sorted_docs(documents, lambda d: d.get("doc_type") == "research"),
        _format_research,
    )

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

    print("Specify --write or --check")
    return 1


if __name__ == "__main__":
    sys.exit(main())

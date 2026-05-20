#!/usr/bin/env python3
"""Build docs/registry/docs_registry.yaml from git-tracked *.md + path overrides YAML.

Run after adding/removing markdown: ``poetry run python scripts/build_docs_registry.py``

Path-level ``doc_id`` and role fixes live in ``docs/registry/path_overrides.yaml``
(``override_guard.max_paths`` prevents unbounded exception growth). Emitted
``docs_registry.yaml`` is the committed artifact; conformance is
``scripts/verify_doc_registry.py`` + Pydantic (`scripts/doc_registry_schema.py`)."""

from __future__ import annotations

import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs" / "registry" / "docs_registry.yaml"
PATH_OVERRIDES_PATH = ROOT / "docs" / "registry" / "path_overrides.yaml"


# Domain prefix for sequential doc_id assignment when not overridden.
DOMAIN_PREFIX_FOR_FIRST_SEGMENT = {
    "reports": "REP",
    "docs": "DOCS",
    "module_a_population_segmentation": "MODA",
    "module_b_resource_allocation": "MODB",
    "module_c_forecasting_scenarios": "MODC",
    "notebooklm-sources-2026-05-14": "RES",
    "appendix": "CAL",
    "schema_contracts": "SCH",
    "tests": "TST",
    "maintainer": "MAINT",
}


def git_tracked_md() -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--", "*.md"],
        check=True,
        capture_output=True,
    )
    raw = proc.stdout.split(b"\0")
    paths: list[str] = []
    for b in raw:
        if not b:
            continue
        paths.append(b.decode("utf-8", errors="replace"))
    paths.sort()
    return paths


def domain_for(path: str) -> str:
    seg = path.split("/", 1)[0]
    if path.startswith(".cursor/"):
        return "CURSOR"
    if path.startswith(".claude/"):
        return "CLAUDE"
    if path.startswith("maintainer/evidence/"):
        return "EVID"
    if path.startswith("maintainer/archive/"):
        return "ARCHV"
    if path.startswith("maintainer/doc_debt/"):
        return "DEBT"
    if path.startswith("maintainer/"):
        return "MAINT"
    if path.startswith("module_c_forecasting_scenarios/reports/research/"):
        return "MODCRS"
    return DOMAIN_PREFIX_FOR_FIRST_SEGMENT.get(seg, "DOC")


def load_override_paths() -> dict[str, dict[str, Any]]:
    """Registry generation policy keyed by markdown path — see docs/registry/path_overrides.yaml."""
    if not PATH_OVERRIDES_PATH.is_file():
        raise SystemExit(f"missing path overrides file: {PATH_OVERRIDES_PATH}")
    raw = yaml.safe_load(PATH_OVERRIDES_PATH.read_text(encoding="utf-8")) or {}
    guard = raw.get("override_guard") or {}
    max_paths = int(guard.get("max_paths", 0))
    paths = dict(raw.get("paths") or {})
    if max_paths <= 0:
        raise SystemExit(f"{PATH_OVERRIDES_PATH}: override_guard.max_paths must be positive")
    if len(paths) > max_paths:
        raise SystemExit(
            f"{PATH_OVERRIDES_PATH}: {len(paths)} override paths exceed "
            f"override_guard.max_paths={max_paths} "
            "(raise max_paths only with reports/decision_log.md or maintainer/doc_debt note)",
        )
    return paths


OVERRIDE: dict[str, dict[str, Any]] = load_override_paths()


def merged_entry(path: str, seq_counters: defaultdict[str, int]) -> dict[str, Any]:
    o = OVERRIDE.get(path, {}).copy()
    for _meta in ("justification", "note"):
        o.pop(_meta, None)

    assigned_id = str(o.pop("doc_id", "")).strip()

    segment_domain = domain_for(path)

    seg = path.split("/", 1)[0]
    if path == "docs/INDEX.md":
        defaults = {
            "doc_type": "registry",
            "doc_role": "registry",
            "visibility": "public",
            "audience": ["portfolio", "agent", "maintainer"],
            "authority": "registry",
            "status": "generated",
            "sensitivity": "public",
            "owner": "architecture",
            "tier_shorthand": "T1",
            "canonical_source": [],
            "derived_from": [],
            "supersedes": [],
            "numeric_authority": [],
            "frontmatter_required": False,
        }
    elif seg == "notebooklm-sources-2026-05-14":
        defaults: dict[str, Any] = {
            "doc_type": "research",
            "doc_role": "reference",
            "visibility": "public",
            "audience": ["portfolio"],
            "authority": "reference_only",
            "status": "active",
            "sensitivity": "public",
            "owner": "research",
            "tier_shorthand": "T4",
            "canonical_source": [],
            "derived_from": [],
            "supersedes": [],
            "numeric_authority": [],
            "frontmatter_required": True,
        }
    elif path.startswith("module_c_forecasting_scenarios/reports/research/"):
        defaults = {
            "doc_type": "methodology",
            "doc_role": "derived",
            "visibility": "public",
            "audience": ["technical"],
            "authority": "derived",
            "status": "active",
            "sensitivity": "public",
            "owner": "module_c",
            "canonical_source": ["DOC-MODC-001"],
            "derived_from": ["DOC-MODC-001"],
            "allowed_content": ["interpretation", "summarization"],
            "forbidden_content": ["novel_metrics", "novel_claims"],
            "numeric_authority": [],
            "frontmatter_required": True,
        }
    elif path.startswith("maintainer/evidence/"):
        defaults = {
            "doc_type": "evidence",
            "doc_role": "evidence",
            "visibility": "internal",
            "audience": ["maintainer", "agent"],
            "authority": "evidence",
            "status": "archived",
            "sensitivity": "internal",
            "owner": "harness",
            "canonical_source": [],
            "derived_from": [],
            "supersedes": [],
            "numeric_authority": [],
            "frontmatter_required": True,
            "tier_shorthand": "T3",
        }
    elif path.startswith(".cursor/") or path.startswith(".claude/"):
        defaults = {
            "doc_type": "policy",
            "doc_role": "canonical",
            "visibility": "internal",
            "audience": ["agent"],
            "authority": "canonical",
            "status": "active",
            "sensitivity": "internal",
            "owner": "harness",
            "tier_shorthand": "T3",
            "canonical_source": [],
            "derived_from": [],
            "supersedes": [],
            "numeric_authority": [],
            "frontmatter_required": True,
        }
    else:
        defaults = {
            "doc_type": "narrative",
            "doc_role": "canonical",
            "visibility": "public",
            "audience": ["portfolio", "technical"],
            "authority": "canonical",
            "status": "active",
            "sensitivity": "public",
            "owner": "project",
            "tier_shorthand": "T1",
            "canonical_source": [],
            "derived_from": [],
            "supersedes": [],
            "numeric_authority": [],
            "frontmatter_required": True,
        }

    defaults.update(o)
    if not assigned_id:
        seq_counters[segment_domain] += 1
        assigned_id = f"DOC-{segment_domain}-{seq_counters[segment_domain]:03d}"
    defaults["doc_id"] = assigned_id
    defaults.setdefault("path", path)
    defaults.setdefault("last_reviewed", "2026-05-20")
    defaults.setdefault("canonical_source", [])
    defaults.setdefault("derived_from", [])
    defaults.setdefault("supersedes", [])
    defaults.setdefault("numeric_authority", [])
    defaults.setdefault("frontmatter_required", True)
    return defaults


def build(
    *,
    expected_count: int | None = None,
) -> list[dict[str, Any]]:
    paths = git_tracked_md()
    if expected_count is not None and len(paths) != expected_count:
        raise SystemExit(
            f"git ls-files *.md count {len(paths)} != expected {expected_count} — "
            "update registry builder / overrides after adding docs",
        )
    counters: defaultdict[str, int] = defaultdict(int)
    used_ids: set[str] = set()
    documents: list[dict[str, Any]] = []
    for path in paths:
        entry = merged_entry(path, counters)
        did = entry["doc_id"]
        if did in used_ids:
            raise SystemExit(f"duplicate doc_id {did} for path {path}")
        used_ids.add(did)
        documents.append(entry)
    return documents


def main() -> int:
    documents = build()
    payload = {
        "schema_version": 1,
        "numeric_namespaces": {
            "campaign_budget_usd": {
                "sources": [
                    "module_b_resource_allocation/src/module_b_resource_allocation/constants.py",
                    "schema_contracts/budget_envelope.yaml",
                ],
                "allow_in_docs": ["DOC-DLOG-001"],
            }
        },
        "documents": documents,
    }
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Wrote {REGISTRY_PATH} ({len(documents)} documents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

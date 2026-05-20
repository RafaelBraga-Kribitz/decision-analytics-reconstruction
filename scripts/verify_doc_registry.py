#!/usr/bin/env python3
"""Validate docs/registry/docs_registry.yaml — structural schema, IDs, paths, lineage."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml
from pydantic import ValidationError

from scripts.doc_registry_schema import parse_registry_payload

REGISTRY_YAML = ROOT / "docs/registry/docs_registry.yaml"
TAXONOMY = ROOT / "docs/registry/taxonomy.yaml"
LIFE = ROOT / "docs/registry/lifecycle.yaml"
PRECEDENCE = ROOT / "docs/registry/authority_precedence.yaml"


def git_tracked_md() -> set[str]:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--", "*.md"],
        check=True,
        capture_output=True,
    )
    return {b.decode("utf-8", errors="replace") for b in proc.stdout.split(b"\0") if b}


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main() -> int:
    if not REGISTRY_YAML.is_file():
        print(f"verify_doc_registry FAILED: missing {REGISTRY_YAML}")
        return 1

    raw_reg = load_yaml(REGISTRY_YAML)
    try:
        modeled = parse_registry_payload(raw_reg)
    except ValidationError as exc:
        print("verify_doc_registry FAILED: registry schema validation")
        print(exc)
        return 1

    reg = modeled.model_dump(mode="python")
    tax = load_yaml(TAXONOMY)
    life = load_yaml(LIFE)
    prec = load_yaml(PRECEDENCE)

    allowed_status = set(str(s) for s in life.get("statuses", []))
    allowed_roles = set(str(x) for x in tax.get("doc_role_values", []))
    allowed_types = set(str(k) for k in (tax.get("doc_types") or {}))
    allowed_auth = set(str(x) for x in tax.get("authority_values", []))
    allowed_vis = set(str(x) for x in tax.get("visibility_values", []))
    gov_subjects_allowed = [str(x) for x in (tax.get("governance_subject_values") or [])]

    rank_list = [str(x) for x in (prec.get("authority_rank") or [])]
    if set(rank_list) != allowed_auth:
        print(
            "verify_doc_registry FAILED: authority_precedence.yaml authority_rank must be a "
            "permutation of taxonomy authority_values",
        )
        print(f"  precedence only in taxonomy: {sorted(set(rank_list) - allowed_auth)}")
        print(f"  taxonomy only in precedence: {sorted(allowed_auth - set(rank_list))}")
        return 1
    rank_idx = {name: i for i, name in enumerate(rank_list)}

    documents: list[dict[str, Any]] = reg["documents"]
    tracked = git_tracked_md()
    registry_paths = {str(d["path"]) for d in documents}

    problems: list[str] = []

    # governance_subject policy
    if gov_subjects_allowed:
        subj_to_paths: dict[str, list[str]] = {}
        for d in documents:
            gs = d.get("governance_subject")
            if gs is None:
                continue
            gs_s = str(gs).strip()
            if gs_s not in gov_subjects_allowed:
                problems.append(f"{d['path']}: governance_subject {gs_s!r} not in taxonomy list")
                continue
            auth_s = str(d.get("authority", ""))
            drole_s = str(d.get("doc_role", ""))
            if auth_s == "canonical" and drole_s == "canonical":
                subj_to_paths.setdefault(gs_s, []).append(str(d["path"]))
        for gs_s, paths_list in subj_to_paths.items():
            if len(paths_list) > 1:
                problems.append(
                    f"governance_subject {gs_s!r}: multiple canonical+canonical docs {paths_list}",
                )
    else:
        for d in documents:
            if d.get("governance_subject"):
                problems.append(
                    f"{d['path']}: governance_subject set but taxonomy governance_subject_values "
                    "is empty — add allowed slugs first",
                )

    if tracked != registry_paths:
        only_git = sorted(tracked - registry_paths)
        only_reg = sorted(registry_paths - tracked)
        if only_git:
            problems.append(
                f"markdown tracked in git missing from docs_registry.yaml ({len(only_git)}):\n  "
                + "\n  ".join(only_git[:50]),
            )
            if len(only_git) > 50:
                problems.append(f"  … and {len(only_git) - 50} more")
        if only_reg:
            problems.append(
                f"registry paths missing from git ls-files (*.md) ({len(only_reg)}):\n  "
                + "\n  ".join(only_reg[:50]),
            )

    by_id: dict[str, dict[str, Any]] = {}
    for d in documents:
        did = d["doc_id"]
        if did in by_id:
            problems.append(
                f"duplicate doc_id {did} for paths {by_id[did]['path']} and {d['path']}",
            )
        by_id[did] = d
        path = ROOT / str(d["path"])
        if not path.is_file():
            problems.append(f"missing path on disk: {d['path']}")

        st = str(d.get("status", "active"))
        if st not in allowed_status:
            problems.append(f"{d['path']}: invalid status {st!r}")

        dr = str(d.get("doc_role", ""))
        if dr not in allowed_roles:
            problems.append(f"{d['path']}: invalid doc_role {dr!r}")

        dt = str(d.get("doc_type", ""))
        if dt not in allowed_types:
            problems.append(f"{d['path']}: invalid doc_type {dt!r}")

        auth = str(d.get("authority", ""))
        if auth not in allowed_auth:
            problems.append(f"{d['path']}: invalid authority {auth!r}")

        vis = str(d.get("visibility", ""))
        if vis not in allowed_vis:
            problems.append(f"{d['path']}: invalid visibility {vis!r}")

        dtype = dt
        if dtype == "evidence" and dr != "evidence":
            problems.append(f"{d['path']}: doc_type evidence requires doc_role evidence")
        if dr == "evidence" and d.get("authority") != "evidence":
            problems.append(f"{d['path']}: doc_role evidence requires authority evidence")
        if (dr == "evidence" or dtype == "evidence") and d.get("authority") == "canonical":
            problems.append(f"{d['path']}: evidence docs cannot use authority canonical")

        if dr == "reference" and d.get("authority") != "reference_only":
            problems.append(f"{d['path']}: doc_role reference requires authority reference_only")

        if dr == "derived" and dtype != "research":
            canon = d.get("canonical_source") or []
            if not canon:
                problems.append(
                    f"{d['path']}: derived docs must declare canonical_source (doc ids)",
                )

        if dr == "canonical" and dtype == "research":
            problems.append(f"{d['path']}: research cannot be doc_role canonical")

    for d in documents:
        for fld in ("canonical_source", "derived_from", "supersedes"):
            refs = d.get(fld) or []
            if not isinstance(refs, list):
                problems.append(f"{d['path']}: {fld} must be a list")
                continue
            for rid in refs:
                if rid not in by_id:
                    problems.append(f"{d['path']}: {fld} references missing doc_id {rid}")
        canon = d.get("canonical_source") or []
        for rid in canon:
            canon_doc = by_id.get(rid)
            if canon_doc is None:
                continue
            cauth = str(canon_doc.get("authority", ""))
            cstatus = str(canon_doc.get("status", ""))
            if cauth not in {"canonical", "registry"}:
                problems.append(f"{d['path']}: canonical_source {rid} has authority {cauth}")
            dst = str(d.get("status", "active"))
            if (
                cstatus in {"archived", "deprecated"}
                and dst == "active"
                and d.get("doc_role") == "derived"
            ):
                problems.append(
                    f"{d['path']}: active derived doc references canonical_source {rid} "
                    f"with status {cstatus}",
                )
            # Precedence-aware: derived lineage must cite stronger-or-equal authority
            citing_auth = str(d.get("authority", ""))
            if (
                str(d.get("doc_role")) == "derived"
                and citing_auth in rank_idx
                and cauth in rank_idx
            ) and rank_idx[cauth] > rank_idx[citing_auth]:
                problems.append(
                    f"{d['path']}: canonical_source {rid} authority {cauth} is weaker than "
                    f"this document authority {citing_auth} per authority_precedence.yaml",
                )

    # Supersedes: superseded docs should not remain active trackers
    for d in documents:
        for sid in d.get("supersedes") or []:
            tgt = by_id.get(sid)
            if not tgt:
                continue
            tst = str(tgt.get("status", "active"))
            if tst not in {"archived", "deprecated"}:
                problems.append(
                    f"{d['path']}: supersedes {sid} ({tgt['path']}) "
                    f"expects status archived|deprecated got {tst!r}",
                )

    if problems:
        print("verify_doc_registry FAILED:\n" + "\n".join(problems[:200]))
        if len(problems) > 200:
            print(f"... and {len(problems) - 200} more")
        return 1
    print(f"verify_doc_registry OK ({len(documents)} documents)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

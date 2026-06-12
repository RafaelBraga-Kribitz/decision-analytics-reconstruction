#!/usr/bin/env python3
"""Validate docs/registry/docs_registry.yaml — structural schema, IDs, paths, lineage."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
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


@dataclass(frozen=True)
class RegistryTaxonomy:
    allowed_status: set[str]
    allowed_roles: set[str]
    allowed_types: set[str]
    allowed_auth: set[str]
    allowed_vis: set[str]
    gov_subjects_allowed: list[str]
    rank_idx: dict[str, int]


def _authority_rank_error(rank_list: list[str], allowed_auth: set[str]) -> str | None:
    if set(rank_list) == allowed_auth:
        return None
    return (
        "verify_doc_registry FAILED: authority_precedence.yaml authority_rank must be a "
        "permutation of taxonomy authority_values\n"
        f"  precedence only in taxonomy: {sorted(set(rank_list) - allowed_auth)}\n"
        f"  taxonomy only in precedence: {sorted(allowed_auth - set(rank_list))}"
    )


def _taxonomy_sets(tax: dict[str, Any], life: dict[str, Any]) -> dict[str, Any]:
    return {
        "allowed_status": {str(s) for s in life.get("statuses", [])},
        "allowed_roles": {str(x) for x in tax.get("doc_role_values", [])},
        "allowed_types": {str(k) for k in (tax.get("doc_types") or {})},
        "allowed_auth": {str(x) for x in tax.get("authority_values", [])},
        "allowed_vis": {str(x) for x in tax.get("visibility_values", [])},
        "gov_subjects_allowed": [str(x) for x in (tax.get("governance_subject_values") or [])],
    }


def _load_taxonomy() -> RegistryTaxonomy | str:
    tax = load_yaml(TAXONOMY)
    life = load_yaml(LIFE)
    prec = load_yaml(PRECEDENCE)
    sets = _taxonomy_sets(tax, life)

    rank_list = [str(x) for x in (prec.get("authority_rank") or [])]
    rank_err = _authority_rank_error(rank_list, sets["allowed_auth"])
    if rank_err:
        return rank_err
    rank_idx = {name: i for i, name in enumerate(rank_list)}
    return RegistryTaxonomy(
        allowed_status=sets["allowed_status"],
        allowed_roles=sets["allowed_roles"],
        allowed_types=sets["allowed_types"],
        allowed_auth=sets["allowed_auth"],
        allowed_vis=sets["allowed_vis"],
        gov_subjects_allowed=sets["gov_subjects_allowed"],
        rank_idx=rank_idx,
    )


def _canonical_subject_paths(
    documents: list[dict[str, Any]],
    gov_subjects_allowed: list[str],
) -> tuple[list[str], dict[str, list[str]]]:
    problems: list[str] = []
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
    return problems, subj_to_paths


def _governance_subject_problems(
    documents: list[dict[str, Any]],
    gov_subjects_allowed: list[str],
) -> list[str]:
    if not gov_subjects_allowed:
        return [
            f"{d['path']}: governance_subject set but taxonomy governance_subject_values "
            "is empty — add allowed slugs first"
            for d in documents
            if d.get("governance_subject")
        ]

    problems, subj_to_paths = _canonical_subject_paths(documents, gov_subjects_allowed)
    for gs_s, paths_list in subj_to_paths.items():
        if len(paths_list) > 1:
            problems.append(
                f"governance_subject {gs_s!r}: multiple canonical+canonical docs {paths_list}",
            )
    return problems


def _git_registry_sync_problems(tracked: set[str], registry_paths: set[str]) -> list[str]:
    problems: list[str] = []
    if tracked == registry_paths:
        return problems

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
    return problems


def _taxonomy_field_problems(d: dict[str, Any], taxonomy: RegistryTaxonomy) -> list[str]:
    path = str(d["path"])
    problems: list[str] = []
    st = str(d.get("status", "active"))
    if st not in taxonomy.allowed_status:
        problems.append(f"{path}: invalid status {st!r}")
    dr = str(d.get("doc_role", ""))
    if dr not in taxonomy.allowed_roles:
        problems.append(f"{path}: invalid doc_role {dr!r}")
    dt = str(d.get("doc_type", ""))
    if dt not in taxonomy.allowed_types:
        problems.append(f"{path}: invalid doc_type {dt!r}")
    auth = str(d.get("authority", ""))
    if auth not in taxonomy.allowed_auth:
        problems.append(f"{path}: invalid authority {auth!r}")
    vis = str(d.get("visibility", ""))
    if vis not in taxonomy.allowed_vis:
        problems.append(f"{path}: invalid visibility {vis!r}")
    return problems


def _evidence_role_problems(path: str, dr: str, dt: str, auth: str) -> list[str]:
    problems: list[str] = []
    if dt == "evidence" and dr != "evidence":
        problems.append(f"{path}: doc_type evidence requires doc_role evidence")
    if dr == "evidence" and auth != "evidence":
        problems.append(f"{path}: doc_role evidence requires authority evidence")
    if (dr == "evidence" or dt == "evidence") and auth == "canonical":
        problems.append(f"{path}: evidence docs cannot use authority canonical")
    return problems


def _role_consistency_problems(d: dict[str, Any]) -> list[str]:
    path = str(d["path"])
    dr = str(d.get("doc_role", ""))
    dt = str(d.get("doc_type", ""))
    auth = str(d.get("authority", ""))
    problems = _evidence_role_problems(path, dr, dt, auth)
    if dr == "reference" and auth != "reference_only":
        problems.append(f"{path}: doc_role reference requires authority reference_only")
    if dr == "derived" and dt != "research" and not (d.get("canonical_source") or []):
        problems.append(f"{path}: derived docs must declare canonical_source (doc ids)")
    if dr == "canonical" and dt == "research":
        problems.append(f"{path}: research cannot be doc_role canonical")
    return problems


def _document_field_problems(
    documents: list[dict[str, Any]],
    taxonomy: RegistryTaxonomy,
    by_id: dict[str, dict[str, Any]],
) -> list[str]:
    problems: list[str] = []
    for d in documents:
        did = d["doc_id"]
        if did in by_id:
            problems.append(
                f"duplicate doc_id {did} for paths {by_id[did]['path']} and {d['path']}",
            )
        by_id[did] = d
        if not (ROOT / str(d["path"])).is_file():
            problems.append(f"missing path on disk: {d['path']}")
        problems.extend(_taxonomy_field_problems(d, taxonomy))
        problems.extend(_role_consistency_problems(d))
    return problems


def _lineage_ref_problems(d: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> list[str]:
    problems: list[str] = []
    for fld in ("canonical_source", "derived_from", "supersedes"):
        refs = d.get(fld) or []
        if not isinstance(refs, list):
            problems.append(f"{d['path']}: {fld} must be a list")
            continue
        for rid in refs:
            if rid not in by_id:
                problems.append(f"{d['path']}: {fld} references missing doc_id {rid}")
    return problems


def _canon_ref_stale_problem(
    d: dict[str, Any],
    rid: str,
    cstatus: str,
) -> str | None:
    dst = str(d.get("status", "active"))
    if cstatus not in {"archived", "deprecated"}:
        return None
    if dst != "active" or d.get("doc_role") != "derived":
        return None
    return (
        f"{d['path']}: active derived doc references canonical_source {rid} "
        f"with status {cstatus}"
    )


def _canon_ref_precedence_problem(
    d: dict[str, Any],
    rid: str,
    cauth: str,
    rank_idx: dict[str, int],
) -> str | None:
    citing_auth = str(d.get("authority", ""))
    if str(d.get("doc_role")) != "derived":
        return None
    if citing_auth not in rank_idx or cauth not in rank_idx:
        return None
    if rank_idx[cauth] <= rank_idx[citing_auth]:
        return None
    return (
        f"{d['path']}: canonical_source {rid} authority {cauth} is weaker than "
        f"this document authority {citing_auth} per authority_precedence.yaml"
    )


def _canonical_source_problems(
    d: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    rank_idx: dict[str, int],
) -> list[str]:
    problems: list[str] = []
    for rid in d.get("canonical_source") or []:
        canon_doc = by_id.get(rid)
        if canon_doc is None:
            continue
        cauth = str(canon_doc.get("authority", ""))
        cstatus = str(canon_doc.get("status", ""))
        if cauth not in {"canonical", "registry"}:
            problems.append(f"{d['path']}: canonical_source {rid} has authority {cauth}")
        stale = _canon_ref_stale_problem(d, rid, cstatus)
        if stale:
            problems.append(stale)
        precedence = _canon_ref_precedence_problem(d, rid, cauth, rank_idx)
        if precedence:
            problems.append(precedence)
    return problems


def _lineage_problems(
    documents: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    rank_idx: dict[str, int],
) -> list[str]:
    problems: list[str] = []
    for d in documents:
        problems.extend(_lineage_ref_problems(d, by_id))
        problems.extend(_canonical_source_problems(d, by_id, rank_idx))
    return problems


def _supersedes_problems(
    documents: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
) -> list[str]:
    problems: list[str] = []
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
    return problems


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

    taxonomy_or_err = _load_taxonomy()
    if isinstance(taxonomy_or_err, str):
        print(taxonomy_or_err)
        return 1
    taxonomy = taxonomy_or_err

    documents: list[dict[str, Any]] = modeled.model_dump(mode="python")["documents"]
    tracked = git_tracked_md()
    registry_paths = {str(d["path"]) for d in documents}

    problems: list[str] = []
    problems.extend(_governance_subject_problems(documents, taxonomy.gov_subjects_allowed))
    problems.extend(_git_registry_sync_problems(tracked, registry_paths))

    by_id: dict[str, dict[str, Any]] = {}
    problems.extend(_document_field_problems(documents, taxonomy, by_id))
    problems.extend(_lineage_problems(documents, by_id, taxonomy.rank_idx))
    problems.extend(_supersedes_problems(documents, by_id))

    if problems:
        print("verify_doc_registry FAILED:\n" + "\n".join(problems[:200]))
        if len(problems) > 200:
            print(f"... and {len(problems) - 200} more")
        return 1
    print(f"verify_doc_registry OK ({len(documents)} documents)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

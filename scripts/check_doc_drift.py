#!/usr/bin/env python3
"""Lightweight numeric / review drift checks backed by maintainer/doc_debt/open.yaml."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_YAML = ROOT / "docs" / "registry" / "docs_registry.yaml"
DEBT_OPEN = ROOT / "maintainer" / "doc_debt" / "open.yaml"

# Two common budget scale anchors that must not contradict in the same prose file
# without an explicit debt waiver (see maintainer/doc_debt/open.yaml).
_BUDGET_44M = re.compile(r"\b44\s*(?:\.\d+)?\s*[mM]\b|\$?\s*44[,\s]?000[,\s]?000\b")
_BUDGET_6M = re.compile(r"\b6\s*(?:\.\d+)?\s*[mM]\b|\b6[,\s]?000[,\s]?000\b|\$\s*6\s*[mM]")


def _record_numeric_waiver(row: dict[str, Any], waivers: set[tuple[str, str]]) -> None:
    did = row.get("doc_id")
    if row.get("issue") == "numeric_drift" and isinstance(did, str):
        waivers.add((did, str(row.get("namespace", "*"))))


def _record_stale_derived(
    row: dict[str, Any],
    last_review: dict[str, dict[str, str]],
) -> None:
    did = row.get("doc_id")
    if row.get("issue") != "stale_derived_view" or not isinstance(did, str):
        return
    canon = row.get("canonical_doc_id")
    if isinstance(canon, str):
        last_review[did] = {
            "canonical_updated_after": str(row.get("canonical_updated_after", "")),
            "canon": canon,
        }


def load_debt_waivers() -> tuple[set[tuple[str, str]], dict[str, dict[str, str]]]:
    if not DEBT_OPEN.is_file():
        return set(), {}
    data = yaml.safe_load(DEBT_OPEN.read_text(encoding="utf-8")) or {}
    waivers: set[tuple[str, str]] = set()
    last_review: dict[str, dict[str, str]] = {}
    for row in data.get("debts") or []:
        if str(row.get("status", "open")) != "open":
            continue
        _record_numeric_waiver(row, waivers)
        _record_stale_derived(row, last_review)
    return waivers, last_review


def _has_budget_waiver(did: str, numeric_waivers: set[tuple[str, str]]) -> bool:
    return (did, "campaign_budget_usd") in numeric_waivers or (did, "*") in numeric_waivers


def _check_budget_doc(
    did: str,
    doc: dict[str, Any],
    numeric_waivers: set[tuple[str, str]],
) -> str | None:
    p = ROOT / str(doc["path"])
    txt = p.read_text(encoding="utf-8", errors="replace")
    hits44 = bool(_BUDGET_44M.search(txt))
    hits6 = bool(_BUDGET_6M.search(txt))
    if not (hits44 and hits6):
        return None
    if _has_budget_waiver(did, numeric_waivers):
        return None
    return (
        f"{doc['path']}: ambiguous dual budget anchors (44M-scale vs 6M-scale prose) "
        f"without doc debt waiver for namespace campaign_budget_usd"
    )


def _check_budget_drift(
    allow_budget_ids: set[str],
    by_id: dict[str, dict[str, Any]],
    numeric_waivers: set[tuple[str, str]],
) -> list[str]:
    problems: list[str] = []
    for did in allow_budget_ids:
        doc = by_id.get(did)
        if not doc:
            problems.append(f"numeric_namespaces references unknown doc_id {did}")
            continue
        msg = _check_budget_doc(did, doc, numeric_waivers)
        if msg:
            problems.append(msg)
    return problems


def _check_stale_derived(
    stale_rows: dict[str, dict[str, str]],
    by_id: dict[str, dict[str, Any]],
) -> list[str]:
    problems: list[str] = []
    for derived_id, meta in stale_rows.items():
        drec = by_id.get(derived_id)
        canon = by_id.get(meta["canon"])
        if not drec or not canon:
            problems.append(f"doc debt references unknown doc_id ({derived_id} / {meta['canon']})")
            continue
        drv_date = str(drec.get("last_reviewed", ""))
        cutoff = meta.get("canonical_updated_after", "")
        if cutoff and drv_date and drv_date < cutoff:
            problems.append(
                f"{drec['path']}: stale_derived debt — derived last_reviewed {drv_date} "
                f"< canonical cutoff {cutoff}"
            )
    return problems


def main() -> int:
    numeric_waivers, stale_rows = load_debt_waivers()

    reg = yaml.safe_load(REGISTRY_YAML.read_text(encoding="utf-8"))
    docs = cast(list[dict[str, Any]], reg["documents"])
    by_id = {cast(str, d["doc_id"]): d for d in docs}

    namespaces = cast(dict[str, Any], reg.get("numeric_namespaces") or {})
    budget_cfg = cast(dict[str, Any], namespaces.get("campaign_budget_usd") or {})
    allow_budget_ids = {str(x) for x in (budget_cfg.get("allow_in_docs") or [])}

    problems: list[str] = []
    problems.extend(_check_budget_drift(allow_budget_ids, by_id, numeric_waivers))
    problems.extend(_check_stale_derived(stale_rows, by_id))

    if problems:
        print("check_doc_drift FAILED:\n" + "\n".join(problems))
        return 1

    print("check_doc_drift OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

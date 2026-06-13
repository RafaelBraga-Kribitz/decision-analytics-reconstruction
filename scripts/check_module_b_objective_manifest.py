#!/usr/bin/env python3
"""Verification script for F-076: Module B manifest documents MILP objective."""

from __future__ import annotations

import json
from pathlib import Path

from _governance_check import REPO_ROOT, gate

MANIFEST = REPO_ROOT / "data" / "processed" / "module_b" / "run_manifest_baseline.json"
SPEC = REPO_ROOT / "module_b_resource_allocation" / "SPECIFICATION.md"


def main() -> int:
    gaps: list[str] = []
    if not MANIFEST.is_file():
        return gate("F-076", Path(__file__).name, False, "missing run_manifest_baseline.json")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    obj = manifest.get("objective_function")
    if not obj or "persuasion_adjusted_contacts" not in str(obj).lower():
        gaps.append("run manifest missing objective_function citing persuasion_adjusted_contacts")

    s1_block = (REPO_ROOT / "reports" / "eda" / "generate_eda.py").read_text(encoding="utf-8")
    if "not MILP segment allocation" not in s1_block and "Prorated Display" not in s1_block:
        gaps.append("generate_eda S1 chart missing proration disclosure")

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "objective documented in manifest; S1 proration disclosed"
    return gate("F-076", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())

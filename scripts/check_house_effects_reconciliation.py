#!/usr/bin/env python3
"""Verification script for F-061: single posterior export for C4 and audit table."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from _governance_check import REPO_ROOT, gate

_TRACKING = REPO_ROOT / "data" / "processed" / "module_c" / "run_all" / "tracking"
HOUSES = _TRACKING / "posterior_house_effects.parquet"
MANIFEST = _TRACKING / "run_tracking_manifest.json"
GEN = REPO_ROOT / "reports" / "eda" / "generate_eda.py"


def main() -> int:
    gaps: list[str] = []

    if not HOUSES.is_file():
        return gate("F-061", Path(__file__).name, False, "missing posterior_house_effects.parquet")

    src = GEN.read_text(encoding="utf-8")
    if "retrospective, Series A" not in src:
        gaps.append("C4 chart missing retrospective Series A disclosure")
    if "posterior_house_effects.parquet" not in src:
        gaps.append("generate_eda does not load posterior_house_effects.parquet")

    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if "house_effects_identifiability_note" not in manifest:
            gaps.append("run_tracking_manifest missing identifiability note")
        expected = manifest.get("posterior_house_effects_sha256")
        if expected:
            actual = hashlib.sha256(HOUSES.read_bytes()).hexdigest()
            if actual != expected:
                gaps.append("posterior_house_effects sha256 mismatch vs manifest")

    ok = not gaps
    detail = (
        "; ".join(gaps) if gaps else "house effects single export with identifiability disclosure"
    )
    return gate("F-061", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())

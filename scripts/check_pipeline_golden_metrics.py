#!/usr/bin/env python3
"""Verification script for F-040 (pipeline wiring + golden-metric gates).

Checks, in order:
  1. Structural wiring — dvc.yaml links A->B->C, the Makefile exposes
     pipeline-full, and the Pages workflow runs Module B before Module C.
  2. Golden-metric gates — tests/test_golden_metrics.py passes (the gates
     skip cleanly when pipeline artifacts are absent, e.g. on CI).

Exits 0 with [PASS] when all checks succeed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(msg: str) -> int:
    print(f"[FAIL] {msg}")
    return 1


def main() -> int:
    dvc = (ROOT / "dvc.yaml").read_text()
    if "media_reachability_by_segment_department.csv" not in dvc:
        return fail("dvc.yaml module_b stage missing Module A reachability dependency")
    if "--allocation-parquet" not in dvc or "allocation_baseline.parquet" not in dvc:
        return fail("dvc.yaml module_c stage missing B->C allocation handshake")

    makefile = (ROOT / "Makefile").read_text()
    if "pipeline-full:" not in makefile:
        return fail("Makefile missing pipeline-full target")

    pages = (ROOT / ".github" / "workflows" / "deploy-module-c-pages.yml").read_text()
    if "run_allocation" not in pages or "--allocation-parquet" not in pages:
        return fail("Pages workflow does not run Module B before Module C")

    if not (ROOT / "reports" / "golden_metrics.json").exists():
        return fail("reports/golden_metrics.json missing — run scripts/generate_golden_metrics.py")

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_golden_metrics.py", "-q", "-p", "no:warnings"],
        cwd=ROOT,
    )
    if proc.returncode != 0:
        return fail("golden-metric gates failed (tests/test_golden_metrics.py)")

    print("[PASS] pipeline wiring + golden-metric gates verified (F-040)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

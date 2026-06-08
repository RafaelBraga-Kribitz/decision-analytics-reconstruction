"""Debt ratchet gate — fail when measured technical debt grows past the baseline.

Re-runs the scanner in-memory and compares each ratcheted metric to
governance/DEBT_BASELINE.json. The ratchet only fires on metrics that were
*available on both sides* (baseline + now); a metric whose tool is missing now
is reported as "unmeasured" and does not fail the gate (we can't prove a
regression we can't measure).

  metric grew            -> [FAIL] exit 1   (debt increased — remediate or justify)
  metric shrank          -> [PASS] + hint to run `make debt-scan` to lock the gain
  metric unchanged       -> [PASS]
  tool missing now       -> [WARN] (unmeasured)
  no baseline yet        -> [PASS] (bootstrapping; run `make debt-scan` first)

Also honors absolute thresholds in the baseline: duplication_pct and complexity
counts above their configured max fail even if they didn't grow, so a project
can't sit forever at a bad-but-flat level.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / "governance" / "DEBT_BASELINE.json"

# Allow a small float wobble in percentage metrics (tool nondeterminism).
_EPSILON = 0.05


def main() -> int:
    if not BASELINE_PATH.exists():
        print("[PASS] check_debt_ratchet.py: no DEBT_BASELINE.json yet — run `make debt-scan`")
        return 0

    import debt_scan  # local import so the module is optional

    baseline = json.loads(BASELINE_PATH.read_text())
    current = debt_scan.scan()

    base_metrics = baseline.get("metrics", {})
    cur_metrics = current.get("metrics", {})
    thresholds = baseline.get("thresholds", {})

    regressions: list[str] = []
    improvements: list[str] = []
    warnings: list[str] = []

    for name, base in base_metrics.items():
        if not base.get("available"):
            continue
        cur = cur_metrics.get(name, {})
        if not cur.get("available"):
            warnings.append(f"{name}: tool '{base.get('tool')}' not available now — unmeasured")
            continue
        bv, cv = base["value"], cur["value"]
        if bv is None or cv is None:
            continue
        # Percentages get an epsilon; integer counts are exact.
        grew = (cv - bv) > _EPSILON if isinstance(cv, float) else cv > bv
        shrank = (bv - cv) > _EPSILON if isinstance(cv, float) else cv < bv
        if grew:
            regressions.append(f"{name}: {bv} → {cv}  (tool: {cur['tool']})")
        elif shrank:
            improvements.append(f"{name}: {bv} → {cv}")

    # Absolute-threshold gates (fail even when flat).
    for name, cur in cur_metrics.items():
        if not cur.get("available") or cur["value"] is None:
            continue
        if name.endswith("duplication_pct"):
            cap = thresholds.get("duplication_pct_max")
            if cap is not None and cur["value"] > cap + _EPSILON:
                regressions.append(f"{name}: {cur['value']:.2f}% exceeds max {cap}%")

    for line in improvements:
        print(f"[PASS] debt improved — {line}")
    if improvements:
        print("       → run `make debt-scan` to lock the gain into the baseline")
    for line in warnings:
        print(f"[WARN] {line}")

    if regressions:
        print(f"\n[FAIL] check_debt_ratchet.py: {len(regressions)} debt metric(s) grew:")
        for line in regressions:
            print(f"       {line}")
        print("\n       Remediate the new debt, or if intentional, run `make debt-scan`")
        print("       in a dedicated PR that explains why the baseline moves up.")
        return 1

    measured = sum(1 for v in cur_metrics.values() if v.get("available"))
    print(f"[PASS] check_debt_ratchet.py: {measured} metric(s) at or below baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())

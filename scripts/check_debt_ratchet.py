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


def _metric_grew(bv: object, cv: object) -> bool:
    if isinstance(cv, float):
        return (cv - bv) > _EPSILON  # type: ignore[operator]
    return cv > bv  # type: ignore[operator]


def _metric_shrank(bv: object, cv: object) -> bool:
    if isinstance(cv, float):
        return (bv - cv) > _EPSILON  # type: ignore[operator]
    return cv < bv  # type: ignore[operator]


def _compare_metric(
    name: str,
    base: dict,
    cur: dict,
) -> tuple[str | None, str | None, str | None]:
    """Return (regression, improvement, warning) — at most one is set."""
    if not base.get("available"):
        return None, None, None
    if not cur.get("available"):
        tool = base.get("tool")
        return None, None, f"{name}: tool '{tool}' not available now — unmeasured"
    bv, cv = base["value"], cur["value"]
    if bv is None or cv is None:
        return None, None, None
    if _metric_grew(bv, cv):
        return f"{name}: {bv} → {cv}  (tool: {cur['tool']})", None, None
    if _metric_shrank(bv, cv):
        return None, f"{name}: {bv} → {cv}", None
    return None, None, None


def _duplication_threshold_regressions(
    cur_metrics: dict[str, dict],
    thresholds: dict,
) -> list[str]:
    regressions: list[str] = []
    for name, cur in cur_metrics.items():
        if not cur.get("available") or cur["value"] is None:
            continue
        if not name.endswith("duplication_pct"):
            continue
        cap = thresholds.get("duplication_pct_max")
        if cap is not None and cur["value"] > cap + _EPSILON:
            regressions.append(f"{name}: {cur['value']:.2f}% exceeds max {cap}%")
    return regressions


def _collect_metric_deltas(
    base_metrics: dict[str, dict],
    cur_metrics: dict[str, dict],
) -> tuple[list[str], list[str], list[str]]:
    regressions: list[str] = []
    improvements: list[str] = []
    warnings: list[str] = []
    for name, base in base_metrics.items():
        reg, imp, warn = _compare_metric(name, base, cur_metrics.get(name, {}))
        if reg:
            regressions.append(reg)
        if imp:
            improvements.append(imp)
        if warn:
            warnings.append(warn)
    return regressions, improvements, warnings


def _print_outcome(
    regressions: list[str],
    improvements: list[str],
    warnings: list[str],
    cur_metrics: dict[str, dict],
) -> None:
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
        return
    measured = sum(1 for v in cur_metrics.values() if v.get("available"))
    print(f"[PASS] check_debt_ratchet.py: {measured} metric(s) at or below baseline")


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

    regressions, improvements, warnings = _collect_metric_deltas(base_metrics, cur_metrics)
    regressions.extend(_duplication_threshold_regressions(cur_metrics, thresholds))
    _print_outcome(regressions, improvements, warnings, cur_metrics)
    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())

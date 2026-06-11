#!/usr/bin/env python3
"""Extract canonical pipeline metrics into reports/golden_metrics.json.

Run after `make pipeline-full`. The emitted JSON is the single numeric
source of truth (SSOT) that golden-metric CI gates and reviewer-facing
docs reconcile against (F-023, F-040).

Usage:
    poetry run python scripts/generate_golden_metrics.py
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = ROOT / "reports" / "golden_metrics.json"


def main() -> int:
    manifest_path = DATA / "module_b" / "run_manifest_baseline.json"
    mc_path = DATA / "module_c" / "run_all" / "mc" / "monte_carlo_draws.parquet"
    tracking_manifest_path = (
        DATA / "module_c" / "run_all" / "tracking" / "run_tracking_manifest.json"
    )
    scenario_manifest_path = DATA / "module_c" / "run_all" / "mc" / "scenario_run_manifest.json"

    missing = [p for p in (manifest_path, mc_path, tracking_manifest_path) if not p.exists()]
    if missing:
        print(f"[FAIL] missing pipeline artifacts: {[str(p) for p in missing]}")
        print("       run `make pipeline-full` first")
        return 1

    manifest = json.loads(manifest_path.read_text())
    tracking = json.loads(tracking_manifest_path.read_text())
    mc = pd.read_parquet(mc_path)

    golden: dict = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "note": (
            "Canonical pipeline numbers. Regenerate via "
            "scripts/generate_golden_metrics.py after an intentional model change; "
            "tests/test_golden_metrics.py gates reproduction."
        ),
        "module_b": {
            "solver_status": manifest["solver_status"],
            "total_budget_usd": manifest["total_budget_usd"],
            "total_persuasion_contacts": manifest["total_persuasion_contacts"],
            "objective_value": manifest["lp_diagnostics"]["objective_value"],
            "row_count": manifest["row_count"],
            "provenance": manifest["provenance"],
            "linearized_lift_pct_milp_vs_naive": manifest["baseline_comparison"][
                "efficiency_vs_department_uniform_naive"
            ]["linearized_lift_pct_milp_vs_naive"],
        },
        "module_c": {
            "calibration_series": tracking["calibration_series"],
            "m_star_pp": tracking["m_star_pp"],
            "outcome_event_date": tracking["outcome_event_date"],
            "n_tracking_waves": tracking["n_tracking_waves"],
            "mc_n_draws": int(len(mc)),
            "mc_alloc_mean_persuasion_contacts": float(mc["alloc_mean_persuasion_contacts"].mean()),
        },
    }
    if scenario_manifest_path.exists():
        scenario = json.loads(scenario_manifest_path.read_text())
        golden["module_c"]["mc_allocation_input"] = scenario.get("allocation_input")

    OUT.write_text(json.dumps(golden, indent=2) + "\n")
    print(f"[PASS] wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

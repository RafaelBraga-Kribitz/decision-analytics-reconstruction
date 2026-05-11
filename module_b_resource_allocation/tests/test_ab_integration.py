"""Cross-module integration checks (A feature stack → B allocation).

Full ``population_segmentation.pipeline.export`` is opt-in via ``RUN_AB_E2E=1``
because it is CPU-heavy on small machines.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from module_b_resource_allocation.constants import ALLOCATION_ROWS
from module_b_resource_allocation.models.allocation import build_problem, solve
from module_b_resource_allocation.models.counterfactual import (
    build_reallocation_counterfactuals_table,
    run_broadcast_to_direct,
)
from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix
from module_b_resource_allocation.utils.allocation_output_gate import (
    validate_allocation_output_df,
)


def test_baseline_solve_matches_contract_row_count() -> None:
    r = solve(build_problem(scenario_id="baseline", solver_seed=42))
    assert len(r.allocation) == ALLOCATION_ROWS
    validate_allocation_output_df(r.allocation)


def test_reallocation_counterfactuals_table_columns() -> None:
    base = solve(build_problem(scenario_id="baseline", solver_seed=42))
    route = build_cost_matrix(scenario="dry_standard", seed=42)
    cf = run_broadcast_to_direct(base, route, shift_share=0.25)
    tbl = build_reallocation_counterfactuals_table(cf)
    for col in (
        "department",
        "channel",
        "week_index",
        "scenario_id",
        "baseline_expected_contacts",
        "counterfactual_expected_contacts",
        "baseline_budget_usd",
        "counterfactual_budget_usd",
        "delta_contacts",
        "delta_budget_usd",
    ):
        assert col in tbl.columns
    assert str(tbl["delta_contacts"].dtype) == "int64"


@pytest.mark.skipif(not os.environ.get("RUN_AB_E2E"), reason="set RUN_AB_E2E=1 to run")
def test_module_a_export_then_b_contract(tmp_path: Path) -> None:
    import yaml
    from population_segmentation.pipeline.export import run_export

    repo = Path(__file__).resolve().parents[2]
    cfg_path = repo / "module_a_population_segmentation/config/generation.yaml"
    anchors_path = repo / "module_a_population_segmentation/config/calibration_anchors.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    cfg = dict(cfg)
    cfg["sample_size"] = 2500
    with open(anchors_path) as f:
        anchors = yaml.safe_load(f)
    run_export(cfg, anchors, tmp_path, sample_size=2500)
    r = solve(build_problem(scenario_id="baseline", solver_seed=42))
    validate_allocation_output_df(r.allocation)

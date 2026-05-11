"""CLI entrypoint: run a Module B allocation end-to-end.

Usage::

    poetry run python -m module_b_resource_allocation.pipeline.run_allocation \
        --scenario baseline \
        --out-dir data/processed/module_b \
        --seed 20180422

Outputs (CSV + Parquet):

* ``allocation_<scenario>.csv`` / ``.parquet`` — schema_contracts/allocation_output.yaml
* ``reach_caps_<scenario>.csv`` — schema_contracts/reachability_caps_dept_channel.yaml
* ``fx_layer_<series>.csv`` — per-week REF/RETAIL rates
* ``run_manifest_<scenario>.json`` — solver metadata + provenance
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from module_b_resource_allocation.constants import VALID_SCENARIOS
from module_b_resource_allocation.data.fx import fx_layer_to_frame, load_fx_layer
from module_b_resource_allocation.models.allocation import build_problem, solve
from module_b_resource_allocation.models.counterfactual import run_broadcast_to_direct
from module_b_resource_allocation.models.feature_join import build_allocation_features
from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Module B allocation pipeline.")
    parser.add_argument(
        "--scenario",
        default="baseline",
        choices=sorted(VALID_SCENARIOS),
    )
    parser.add_argument(
        "--fx-series",
        default="series_b_weekly",
        choices=["series_a_monthly", "series_b_weekly"],
    )
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20180422)
    parser.add_argument("--routing-scenario", default="dry_standard")
    parser.add_argument(
        "--counterfactual",
        action="store_true",
        help="Also produce the broadcast_to_direct counterfactual allocation.",
    )
    parser.add_argument("--shift-share", type=float, default=0.30)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[run_allocation] scenario={args.scenario} seed={args.seed}", flush=True)
    problem = build_problem(
        scenario_id=args.scenario,
        fx_series_id=args.fx_series,  # type: ignore[arg-type]
        solver_seed=args.seed,
    )
    result = solve(problem)
    print(
        f"[run_allocation] solver_status={result.solver_status} "
        f"total_usd={result.total_budget_usd:.2f}",
        flush=True,
    )

    alloc_csv = args.out_dir / f"allocation_{args.scenario}.csv"
    alloc_parquet = args.out_dir / f"allocation_{args.scenario}.parquet"
    result.allocation.to_csv(alloc_csv, index=False)
    result.allocation.to_parquet(alloc_parquet, index=False)

    reach_caps = build_allocation_features()
    reach_csv = args.out_dir / f"reach_caps_{args.scenario}.csv"
    reach_caps.to_csv(reach_csv, index=False)

    fx_df = fx_layer_to_frame(load_fx_layer(args.fx_series))  # type: ignore[arg-type]
    fx_csv = args.out_dir / f"fx_layer_{args.fx_series}.csv"
    fx_df.to_csv(fx_csv, index=False)

    routing_df = build_cost_matrix(scenario=args.routing_scenario, seed=args.seed)
    routing_csv = args.out_dir / f"routing_cost_matrix_{args.routing_scenario}.csv"
    routing_df.to_csv(routing_csv, index=False)

    artifacts: dict[str, str] = {
        "allocation_csv": str(alloc_csv),
        "allocation_parquet": str(alloc_parquet),
        "reach_caps_csv": str(reach_csv),
        "fx_layer_csv": str(fx_csv),
        "routing_cost_csv": str(routing_csv),
    }

    if args.counterfactual:
        cf = run_broadcast_to_direct(result, routing_df, shift_share=args.shift_share)
        cf_csv = args.out_dir / "allocation_broadcast_to_direct.csv"
        deltas_csv = args.out_dir / "allocation_broadcast_to_direct_deltas.csv"
        cf.counterfactual_allocation.to_csv(cf_csv, index=False)
        cf.deltas.to_csv(deltas_csv, index=False)
        artifacts["counterfactual_csv"] = str(cf_csv)
        artifacts["counterfactual_deltas_csv"] = str(deltas_csv)
        artifacts["routing_feasible_share"] = str(round(cf.routing_feasible_share, 4))

    manifest = {
        "run_id": datetime.now(UTC).isoformat(),
        "scenario_id": args.scenario,
        "fx_series_id": args.fx_series,
        "routing_scenario": args.routing_scenario,
        "solver_seed": args.seed,
        "solver_status": result.solver_status,
        "total_budget_usd": round(result.total_budget_usd, 4),
        "total_persuasion_contacts": round(
            float(result.allocation["persuasion_adjusted_contacts"].sum()), 2
        ),
        "row_count": int(len(result.allocation)),
        "artifacts": artifacts,
        "provenance": "PRIOR",
        "module_b_version": "0.1.0",
    }
    manifest_path = args.out_dir / f"run_manifest_{args.scenario}.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[run_allocation] manifest written to {manifest_path}", flush=True)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI dispatch
    sys.exit(main())

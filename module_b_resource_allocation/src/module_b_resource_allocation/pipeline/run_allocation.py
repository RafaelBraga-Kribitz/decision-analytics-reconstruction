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
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pandas as pd

from module_b_resource_allocation.constants import VALID_SCENARIOS
from module_b_resource_allocation.data.fx import fx_layer_to_frame, load_fx_layer
from module_b_resource_allocation.models.allocation import build_problem, solve
from module_b_resource_allocation.models.counterfactual import (
    build_reallocation_counterfactuals_table,
    run_broadcast_to_direct,
)
from module_b_resource_allocation.models.feature_join import build_allocation_features
from module_b_resource_allocation.reporting.baselines import build_baseline_comparison_for_run
from module_b_resource_allocation.reporting.budget_sensitivity import (
    compute_budget_expansion_curve,
)
from module_b_resource_allocation.reporting.duals_export import (
    write_budget_dual_csv,
    write_reach_cap_duals_csv,
)
from module_b_resource_allocation.reporting.run_markdown import render_allocation_run_markdown
from module_b_resource_allocation.reporting.scenario_benchmark import write_scenario_benchmark_csv
from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix
from module_b_resource_allocation.utils.allocation_output_gate import (
    validate_allocation_output_df,
)

logger = logging.getLogger(__name__)


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
    parser.add_argument(
        "--sensitivity",
        action="store_true",
        help=(
            "Run budget expansion re-solves (0.25–2.0× envelope) and attach LP dual "
            "snapshot to the run manifest (slower)."
        ),
    )
    return parser.parse_args(argv)


def _write_allocation_artifacts(
    result: Any, args: argparse.Namespace
) -> tuple[dict[str, str], int]:
    alloc_csv = args.out_dir / f"allocation_{args.scenario}.csv"
    alloc_parquet = args.out_dir / f"allocation_{args.scenario}.parquet"
    try:
        result.allocation.to_csv(alloc_csv, index=False)
        result.allocation.to_parquet(alloc_parquet, index=False)
    except OSError as exc:
        logger.exception("failed writing allocation artifacts: %s", exc)
        return {}, 4
    return {
        "allocation_csv": str(alloc_csv),
        "allocation_parquet": str(alloc_parquet),
    }, 0


def _write_secondary_artifacts(
    args: argparse.Namespace,
) -> tuple[dict[str, str], pd.DataFrame, pd.DataFrame, int]:
    try:
        reach_caps = build_allocation_features()
        reach_csv = args.out_dir / f"reach_caps_{args.scenario}.csv"
        reach_caps.to_csv(reach_csv, index=False)

        fx_df = fx_layer_to_frame(load_fx_layer(args.fx_series))  # type: ignore[arg-type]
        fx_csv = args.out_dir / f"fx_layer_{args.fx_series}.csv"
        fx_df.to_csv(fx_csv, index=False)

        routing_df = build_cost_matrix(scenario=args.routing_scenario, seed=args.seed)
        routing_csv = args.out_dir / f"routing_cost_matrix_{args.routing_scenario}.csv"
        routing_df.to_csv(routing_csv, index=False)
    except OSError as exc:
        logger.exception("failed writing secondary artifacts: %s", exc)
        return {}, pd.DataFrame(), pd.DataFrame(), 4
    return (
        {
            "reach_caps_csv": str(reach_csv),
            "fx_layer_csv": str(fx_csv),
            "routing_cost_csv": str(routing_csv),
        },
        reach_caps,
        routing_df,
        0,
    )


def _write_counterfactual_artifacts(
    result: Any,
    routing_df: pd.DataFrame,
    reach_caps: pd.DataFrame,
    args: argparse.Namespace,
) -> tuple[dict[str, str], int]:
    cf = run_broadcast_to_direct(result, routing_df, shift_share=args.shift_share)
    cf_csv = args.out_dir / "allocation_broadcast_to_direct.csv"
    cf_parquet = args.out_dir / "allocation_broadcast_to_direct.parquet"
    cf_caps_csv = args.out_dir / "reach_caps_broadcast_to_direct.csv"
    deltas_csv = args.out_dir / "allocation_broadcast_to_direct_deltas.csv"
    rc_parquet = args.out_dir / "reallocation_counterfactuals.parquet"
    try:
        cf.counterfactual_allocation.to_csv(cf_csv, index=False)
        cf.counterfactual_allocation.to_parquet(cf_parquet, index=False)
        reach_caps.to_csv(cf_caps_csv, index=False)
        cf.deltas.to_csv(deltas_csv, index=False)
        build_reallocation_counterfactuals_table(cf).to_parquet(rc_parquet, index=False)
    except OSError as exc:
        logger.exception("failed writing counterfactual artifacts: %s", exc)
        return {}, 4
    return {
        "counterfactual_csv": str(cf_csv),
        "counterfactual_parquet": str(cf_parquet),
        "counterfactual_reach_caps_csv": str(cf_caps_csv),
        "counterfactual_deltas_csv": str(deltas_csv),
        "reallocation_counterfactuals_parquet": str(rc_parquet),
        "routing_feasible_share": str(round(cf.routing_feasible_share, 4)),
    }, 0


def _attach_sensitivity_artifacts(
    problem: Any,
    result: Any,
    args: argparse.Namespace,
    artifacts: dict[str, str],
    baseline_comparison_payload: dict[str, object],
) -> dict[str, object]:
    manifest_extras: dict[str, object] = {}
    curve = compute_budget_expansion_curve(
        scenario_id=args.scenario,
        fx_series_id=args.fx_series,
        solver_seed=args.seed,
    )
    manifest_extras["budget_expansion_curve"] = curve
    try:
        curve_csv = args.out_dir / f"budget_expansion_curve_{args.scenario}.csv"
        pd.DataFrame(curve).to_csv(curve_csv, index=False)
        artifacts["budget_expansion_curve_csv"] = str(curve_csv)
    except Exception as exc:  # pragma: no cover
        logger.warning("budget expansion CSV skipped: %s", exc)
    try:
        db = write_budget_dual_csv(result, args.out_dir, args.scenario)
        dr = write_reach_cap_duals_csv(result, args.out_dir, args.scenario)
        artifacts["dual_budget_envelope_csv"] = str(db)
        artifacts["dual_reach_caps_csv"] = str(dr)
        bench = args.out_dir / f"scenario_benchmark_{args.scenario}.csv"
        write_scenario_benchmark_csv(bench, fx_series_id=args.fx_series, solver_seed=args.seed)
        artifacts["scenario_benchmark_csv"] = str(bench)
        report_md = args.out_dir / f"allocation_run_{args.scenario}.md"
        report_md.write_text(
            render_allocation_run_markdown(
                result,
                scenario_id=args.scenario,
                fx_series_id=args.fx_series,
                routing_scenario=args.routing_scenario,
                sensitivity_run=True,
                baseline_comparison=cast(dict[str, Any], baseline_comparison_payload),
            ),
            encoding="utf-8",
        )
        artifacts["allocation_run_md"] = str(report_md)
    except Exception as exc:  # pragma: no cover
        logger.warning("dual CSV export skipped: %s", exc)
    return manifest_extras


def main(argv: list[str] | None = None) -> int:
    """Execute the Module B allocation CLI and write artifacts to ``--out-dir``.

    Args:
        argv: Optional argument vector (defaults to ``sys.argv`` when ``None``).

    Returns:
        Process exit code (``0`` success, non-zero for solver/IO failures).

    Raises:
        None: Errors are returned as integer exit codes, not raised exceptions.

    Example:
        ``python -m module_b_resource_allocation.pipeline.run_allocation --help``
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("scenario=%s seed=%s", args.scenario, args.seed)
    try:
        problem = build_problem(
            scenario_id=args.scenario,
            fx_series_id=args.fx_series,  # type: ignore[arg-type]  # argparse Namespace types str | None; build_problem expects str
            solver_seed=args.seed,
        )
        result = solve(problem)
    except Exception as exc:  # pragma: no cover - defensive CLI
        logger.exception("allocation solve failed: %s", exc)
        return 2

    logger.info("solver_status=%s total_usd=%.2f", result.solver_status, result.total_budget_usd)
    try:
        validate_allocation_output_df(result.allocation)
    except ValueError as exc:
        logger.error("allocation_output contract gate: %s", exc)
        return 3

    alloc_artifacts, code = _write_allocation_artifacts(result, args)
    if code != 0:
        return code

    secondary_artifacts, reach_caps, routing_df, code = _write_secondary_artifacts(args)
    if code != 0:
        return code

    artifacts: dict[str, str] = {**alloc_artifacts, **secondary_artifacts}

    if args.counterfactual:
        cf_artifacts, code = _write_counterfactual_artifacts(result, routing_df, reach_caps, args)
        if code != 0:
            return code
        artifacts.update(cf_artifacts)

    baseline_comparison_payload = build_baseline_comparison_for_run(problem, result)
    manifest: dict[str, object] = {
        "run_id": datetime.now(UTC).isoformat(),
        "scenario_id": args.scenario,
        "fx_series_id": args.fx_series,
        "routing_scenario": args.routing_scenario,
        "solver_seed": args.seed,
        "solver_status": result.solver_status,
        "total_budget_usd": round(result.total_budget_usd, 4),
        "total_persuasion_contacts": round(result.total_persuasion_adjusted_contacts, 2),
        "objective_function": (
            "maximize sum(persuasion_adjusted_contacts) over (dept, channel, week) "
            "subject to budget envelope, bundle constraints, and per-dept expected_contacts "
            "coverage floor"
        ),
        "row_count": int(len(result.allocation)),
        "artifacts": artifacts,
        "provenance": (
            "MODULE_A+PRIOR" if (problem.reach_caps["provenance"] == "MODULE_A").any() else "PRIOR"
        ),
        "module_b_version": "0.1.0",
        "lp_diagnostics": result.lp_diagnostics,
        "baseline_comparison": baseline_comparison_payload,
    }
    if args.sensitivity:
        manifest.update(
            _attach_sensitivity_artifacts(
                problem, result, args, artifacts, baseline_comparison_payload
            )
        )
    manifest_path = args.out_dir / f"run_manifest_{args.scenario}.json"
    try:
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
    except OSError as exc:
        logger.exception("failed writing manifest: %s", exc)
        return 4
    logger.info("manifest written to %s", manifest_path)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI dispatch
    sys.exit(main())

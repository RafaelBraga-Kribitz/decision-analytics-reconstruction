#!/usr/bin/env python3
"""Deterministic 'decision replay' generator for the week-8 worked example (issue #100).

This script produces every number cited by the "A worked decision: week 8 replay"
section of ``reports/CASE_STUDY.md``. It walks ONE campaign decision end-to-end:

    week-8 poll posterior  ->  one disclosed solver-input change  ->  Module B
    re-solve  ->  reallocation delta (USD + contacts)  ->  uncertainty band.

Honest wiring disclosure
------------------------
Module C (the tracking posterior) is DOWNSTREAM of Module B in this pipeline
(A -> B feeds reach/propensity into the allocator; B -> C feeds the allocation
into forecasting). The live pipeline therefore does **not** feed the week-8
tracking posterior back into the Module B MILP. This is a *scenario replay*: we
re-parameterize, by hand and fully disclosed, the single solver lever a campaign
WOULD update at mid-campaign given a fresh poll posterior. Nothing here is done
automatically by the pipeline.

The lever
---------
The MILP objective multiplies each cell's expected contacts by a strategic
``tier_penalty`` weight (``models/allocation.py::_TIER_PENALTY``). The swing-tier
weight is the "how hard do we push the contested departments" knob. At plan time
it is the committed value 1.10, which we identify with the plan-time national
lead. The mapping rescales it by how the week-8 posterior lead compares to that
plan-time lead:

    swing_weight(margin) = base_swing_weight * clip(m_plan / margin, 1/3, 3)

so a *wider* lead than assumed pulls emphasis OFF the knife-edge swing
departments (ratio < 1), a *tighter* lead pushes emphasis toward them (ratio > 1).
Elasticity is 1 (inverse proportionality to the lead), bounded to a 3x band. This
is an illustrative, disclosed modeling choice, exactly like the ESTIMATED tier
priors it rescales — never a measured causal quantity.

Uncertainty
-----------
We re-solve at the posterior mean and at both 94% HDI endpoints of the week-8
margin (3 replay solves + 1 baseline). Every solve must return OPTIMAL.

Run::

    poetry run python scripts/generate_decision_replay.py

Writes ``reports/decision_replay_results.json`` (committed evidence) and prints a
markdown table. Output is deterministic: identical bytes on repeated runs.
"""

from __future__ import annotations

import contextlib
import json
import sys
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
from module_b_resource_allocation.models import allocation as alloc

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACKING_PARQUET = (
    REPO_ROOT
    / "data"
    / "processed"
    / "module_c"
    / "run_all"
    / "tracking"
    / "daily_posterior_forecast.parquet"
)
RESULTS_JSON = REPO_ROOT / "reports" / "decision_replay_results.json"

SOLVER_SEED = 20180422
SCENARIO_ID = "baseline"
CALIBRATION_SERIES = "A"
PLAN_WEEK_ISO = "2018-W01"  # end of campaign week 1 == plan-time anchor
REPLAY_WEEK_ISO = "2018-W08"  # end of campaign week 8 == replay anchor
SWING_TIER = "swing"
#: Bound on the emphasis rescale so a single poll update can at most triple or
#: cut-to-a-third the contested-department weight (disclosed illustrative band).
CLIP_LO, CLIP_HI = 1.0 / 3.0, 3.0


class ReplayError(RuntimeError):
    """Raised when an input artifact is missing or a solve is not OPTIMAL."""


@contextlib.contextmanager
def _swing_weight_override(weight: float) -> Iterator[None]:
    """Temporarily set the swing-tier objective weight, then restore it.

    The Module B MILP reads ``_TIER_PENALTY`` at solve time. The replay overrides
    only the swing entry for the duration of one solve and always restores the
    committed dict — the pipeline source is never mutated on disk, and the
    provenance gate (which imports the literal) is unaffected.
    """
    original = dict(alloc._TIER_PENALTY)
    alloc._TIER_PENALTY[SWING_TIER] = float(weight)
    try:
        yield
    finally:
        alloc._TIER_PENALTY.clear()
        alloc._TIER_PENALTY.update(original)


def _read_week_posterior() -> dict[str, dict[str, float]]:
    """Extract the plan-time and week-8 national poll-margin posterior.

    Returns a dict with ``plan`` (mean only) and ``replay`` (mean, hdi_low,
    hdi_high) taken from the last day of each ISO week of the committed Module C
    tracking series.
    """
    if not TRACKING_PARQUET.is_file():
        raise ReplayError(
            f"Module C tracking posterior missing at {TRACKING_PARQUET} — "
            "run the Module C tracking stage first (dvc repro / run_all)."
        )
    df = pd.read_parquet(TRACKING_PARQUET)
    df = df[df["calibration_series"] == CALIBRATION_SERIES].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["iso_week"] = df["date"].dt.strftime("%G-W%V")

    def _last_of_week(iso: str) -> pd.Series:
        wk = df[df["iso_week"] == iso].sort_values("date")
        if wk.empty:
            raise ReplayError(f"tracking series has no rows for ISO week {iso}")
        return wk.iloc[-1]

    plan_row = _last_of_week(PLAN_WEEK_ISO)
    replay_row = _last_of_week(REPLAY_WEEK_ISO)
    return {
        "plan": {
            "iso_week": PLAN_WEEK_ISO,
            "date": str(plan_row["date"].date()),
            "margin_mean_pp": round(float(plan_row["posterior_mean_preference_margin_pp"]), 4),
        },
        "replay": {
            "iso_week": REPLAY_WEEK_ISO,
            "date": str(replay_row["date"].date()),
            "margin_mean_pp": round(float(replay_row["posterior_mean_preference_margin_pp"]), 4),
            "margin_hdi_low_pp": round(float(replay_row["posterior_hdi_low_pp"]), 4),
            "margin_hdi_high_pp": round(float(replay_row["posterior_hdi_high_pp"]), 4),
        },
    }


def _swing_weight(margin_pp: float, m_plan_pp: float, base_weight: float) -> float:
    ratio = max(min(m_plan_pp / margin_pp, CLIP_HI), CLIP_LO)
    return round(base_weight * ratio, 6)


def _solve(weight: float) -> alloc.AllocationResult:
    with _swing_weight_override(weight):
        result = alloc.solve(alloc.build_problem(scenario_id=SCENARIO_ID, solver_seed=SOLVER_SEED))
    if result.solver_status != "OPTIMAL":
        raise ReplayError(f"solve at swing_weight={weight} returned {result.solver_status}")
    return result


def _dept_sum(result: alloc.AllocationResult, column: str) -> pd.Series:
    return result.allocation.groupby("department")[column].sum()


def _rescore_under_weights(
    result: alloc.AllocationResult, swing_weight: float, base_weight: float
) -> float:
    """Score any allocation under a given swing weight (only the swing tier moves)."""
    df = result.allocation
    factor = df["department_tier"].map(
        lambda tier: swing_weight / base_weight if tier == SWING_TIER else 1.0
    )
    return float((df["persuasion_adjusted_contacts"] * factor).sum())


def build_payload() -> dict:
    base_weight = float(alloc._TIER_PENALTY[SWING_TIER])
    posterior = _read_week_posterior()
    m_plan = posterior["plan"]["margin_mean_pp"]
    r = posterior["replay"]

    weights = {
        "baseline": base_weight,
        "week8_mean": _swing_weight(r["margin_mean_pp"], m_plan, base_weight),
        "week8_hdi_low": _swing_weight(r["margin_hdi_low_pp"], m_plan, base_weight),
        "week8_hdi_high": _swing_weight(r["margin_hdi_high_pp"], m_plan, base_weight),
    }
    results = {name: _solve(w) for name, w in weights.items()}

    base = results["baseline"]
    mean = results["week8_mean"]
    tier_map = base.allocation.groupby("department")["department_tier"].first()

    base_usd = _dept_sum(base, "budget_allocation_usd")
    mean_usd = _dept_sum(mean, "budget_allocation_usd")
    low_usd = _dept_sum(results["week8_hdi_low"], "budget_allocation_usd")
    high_usd = _dept_sum(results["week8_hdi_high"], "budget_allocation_usd")
    base_contacts = _dept_sum(base, "expected_contacts")
    mean_contacts = _dept_sum(mean, "expected_contacts")

    rows = []
    for dept in sorted(base_usd.index):
        rows.append(
            {
                "department": dept,
                "tier": str(tier_map[dept]),
                "baseline_usd": round(float(base_usd[dept]), 2),
                "replayed_usd": round(float(mean_usd[dept]), 2),
                "delta_usd": round(float(mean_usd[dept] - base_usd[dept]), 2),
                "delta_expected_contacts": int(round(mean_contacts[dept] - base_contacts[dept])),
                "replay_hdi_low_usd": round(float(low_usd[dept]), 2),
                "replay_hdi_high_usd": round(float(high_usd[dept]), 2),
            }
        )
    rows.sort(key=lambda x: x["delta_usd"])

    # Decision-relevant objective: score BOTH plans under the week-8 belief.
    sw_mean = weights["week8_mean"]
    baseline_under_w8 = _rescore_under_weights(base, sw_mean, base_weight)
    week8_under_w8 = mean.total_persuasion_adjusted_contacts
    value_of_update = week8_under_w8 - baseline_under_w8

    total_shift = sum(r["delta_usd"] for r in rows if r["delta_usd"] > 0)

    payload = {
        "description": (
            "Week-8 decision replay for issue #100. Scenario replay: the week-8 "
            "poll posterior is mapped, via one disclosed lever, to the Module B "
            "swing-tier objective weight; the MILP is re-solved. Illustrative "
            "fixture posterior; no causal claim."
        ),
        "solver_seed": SOLVER_SEED,
        "scenario_id": SCENARIO_ID,
        "posterior": posterior,
        "mapping": {
            "lever": "models/allocation.py::_TIER_PENALTY['swing']",
            "formula": "swing_weight(m) = base_swing_weight * clip(m_plan / m, 1/3, 3)",
            "base_swing_weight": base_weight,
            "m_plan_pp": m_plan,
            "clip_low": round(CLIP_LO, 6),
            "clip_high": round(CLIP_HI, 6),
            "swing_weights": weights,
        },
        "solver_status": {name: res.solver_status for name, res in results.items()},
        "totals": {
            "budget_envelope_usd": round(float(base_usd.sum()), 2),
            "raw_expected_contacts_baseline": int(round(base_contacts.sum())),
            "raw_expected_contacts_week8_mean": int(round(mean_contacts.sum())),
            "raw_expected_contacts_delta": int(round(mean_contacts.sum() - base_contacts.sum())),
            "usd_shifted_off_swing": round(float(total_shift), 2),
            "belief_weighted_baseline_plan": round(baseline_under_w8, 2),
            "belief_weighted_week8_plan": round(week8_under_w8, 2),
            "belief_weighted_value_of_update": round(value_of_update, 2),
            "belief_weighted_value_of_update_pct": round(
                100.0 * value_of_update / baseline_under_w8, 4
            ),
        },
        "departments": rows,
    }
    return payload


def _markdown_table(payload: dict) -> str:
    lines = [
        "| Department | Tier | Baseline $ | Replayed $ | Δ $ | Δ contacts |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in payload["departments"]:
        lines.append(
            f"| {row['department']} | {row['tier']} | "
            f"{row['baseline_usd']:,.0f} | {row['replayed_usd']:,.0f} | "
            f"{row['delta_usd']:,.0f} | {row['delta_expected_contacts']:,d} |"
        )
    return "\n".join(lines)


def main() -> int:
    try:
        payload = build_payload()
    except ReplayError as exc:
        print(f"[decision-replay] ERROR: {exc}", file=sys.stderr)
        return 1
    RESULTS_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[decision-replay] wrote {RESULTS_JSON.relative_to(REPO_ROOT)}")
    print(f"[decision-replay] solver statuses: {payload['solver_status']}")
    t = payload["totals"]
    print(
        f"[decision-replay] shifted ${t['usd_shifted_off_swing']:,.0f} off swing; "
        f"belief-weighted value of update {t['belief_weighted_value_of_update']:,.0f} "
        f"(+{t['belief_weighted_value_of_update_pct']:.2f}%)"
    )
    print(_markdown_table(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())

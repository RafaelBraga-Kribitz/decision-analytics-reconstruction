"""Objective-vs-reported identity gate (F-037).

The MILP must maximize the same quantity the artifacts report. The objective
is the K=6-breakpoint chord interpolant of ``_expected_contacts``; the report
evaluates the exact curve. At a vertex solution the two agree to numerical
noise — a single blended-slope proxy objective (the former bug) diverges by
double-digit percentages.
"""

from __future__ import annotations

import pytest
from module_b_resource_allocation.models.allocation import (
    _pl_segments,  # pyright: ignore[reportPrivateUsage]
    _reach_breakpoints,  # pyright: ignore[reportPrivateUsage]
    build_problem,
    solve,
)


@pytest.fixture(scope="module")
def baseline_result():
    return solve(build_problem(scenario_id="baseline", solver_seed=20180422))


def test_objective_equals_reported_persuasion_contacts(baseline_result) -> None:
    diag = baseline_result.lp_diagnostics
    assert diag is not None and diag.get("objective_value") is not None
    objective = float(diag["objective_value"])
    reported = float(baseline_result.allocation["persuasion_adjusted_contacts"].sum())
    assert reported > 0
    rel_gap = abs(objective - reported) / reported
    assert rel_gap < 0.005, (
        f"objective {objective:.2f} vs reported {reported:.2f} "
        f"(rel gap {rel_gap:.4%}) — optimizer and report disagree"
    )


def test_reach_breakpoints_include_zero_inflection_and_full_reach() -> None:
    bps = _reach_breakpoints(0.45)
    assert bps[0] == 0.0
    assert 0.45 in bps
    assert bps[-1] == 1.0
    assert len(bps) == 6


def test_pl_segments_are_concave_chords() -> None:
    segments = _pl_segments(audience=10_000.0, uc_usd=0.5, k_dim=1.2, inflection=0.4)
    assert segments, "no segments built"
    slopes = [s for _, s in segments]
    assert all(
        a >= b - 1e-12 for a, b in zip(slopes[:-1], slopes[1:], strict=True)
    ), f"segment slopes must be non-increasing (concavity): {slopes}"
    # First segment covers the linear region at full efficiency: slope ≈ 1/uc.
    assert slopes[0] == pytest.approx(1.0 / 0.5, rel=1e-9)

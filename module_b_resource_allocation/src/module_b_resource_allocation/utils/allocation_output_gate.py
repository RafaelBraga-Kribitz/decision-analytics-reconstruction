"""Hard gates for ``allocation_output`` contract (Module B post-solve)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Final, cast

import pandas as pd
import yaml

from module_b_resource_allocation.constants import (
    ALLOCATION_ROWS,
    CHANNEL_NAMES,
    DEPARTMENTS,
    WEEK_COUNT,
)

_SOLVER_OK: Final[tuple[str, ...]] = ("OPTIMAL", "FEASIBLE")

_CONTRACT_PATH: Final[Path] = (
    Path(__file__).resolve().parents[4] / "schema_contracts" / "allocation_output.yaml"
)


@lru_cache(maxsize=1)
def _quality_gates() -> dict[str, Any]:
    """Load the contract's ``quality_gates`` block (contract YAML is the SSOT)."""
    with open(_CONTRACT_PATH) as f:
        contract = yaml.safe_load(f)
    return cast(dict[str, Any], contract.get("quality_gates", {}))


def validate_allocation_output_df(df: pd.DataFrame, *, enforce_coverage: bool = True) -> None:
    """Validate ``df`` against the ``allocation_output`` schema contract.

    Enforces structural gates (row count, keys, canonical labels) plus the
    contract's ``quality_gates``: budget envelope within tolerance, solver
    status allow-list, and the per-department coverage floor.

    Args:
        df: Post-solve allocation table emitted by :func:`solve`.
        enforce_coverage: Set False for counterfactual tables, where spend has
            been heuristically reallocated and the solver's coverage floor no
            longer applies.

    Returns:
        ``None`` when all gates pass.

    Raises:
        ValueError: If any structural or quality gate fails.

    Example:
        ``validate_allocation_output_df(result.allocation)`` at the end of the CLI pipeline.
    """
    errors: list[str] = []
    if len(df) != ALLOCATION_ROWS:
        errors.append(f"row_count: expected {ALLOCATION_ROWS}, got {len(df)}")
    if df.duplicated(["department", "channel", "week_index"]).any():
        errors.append("unique_key: duplicate (department, channel, week_index)")
    gates = _quality_gates()
    allowed_status = tuple(gates.get("solver_status_allow", _SOLVER_OK))
    bad_status = df[~df["solver_status"].isin(allowed_status)]
    if len(bad_status):
        bad_vals = cast(pd.Series, bad_status["solver_status"]).unique().tolist()
        errors.append(f"solver_status: invalid values {bad_vals}")
    if not df["week_index"].between(1, WEEK_COUNT).all():
        errors.append("week_index: out of range")
    bad_ch = set(df["channel"].unique()) - set(CHANNEL_NAMES)
    if bad_ch:
        errors.append(f"channel: non-canonical values {bad_ch}")
    bad_d = set(df["department"].unique()) - set(DEPARTMENTS)
    if bad_d:
        errors.append(f"department: non-canonical values {bad_d}")

    # Quality gate: total budget envelope within tolerance.
    envelope = gates.get("total_budget_envelope_usd")
    tolerance = float(gates.get("total_budget_envelope_tolerance_pct", 0.0))
    if envelope is not None:
        total = float(df["budget_allocation_usd"].sum())
        lo = float(envelope) * (1.0 - tolerance)
        hi = float(envelope) * (1.0 + tolerance)
        if not lo <= total <= hi:
            errors.append(
                f"budget_envelope: total {total:.2f} outside [{lo:.2f}, {hi:.2f}]"
            )

    # Quality gate: per-department coverage floor — expected contacts must
    # reach coverage_lower_bound_pct of the department population proxy
    # (largest single-channel reachable audience).
    coverage_pct = gates.get("coverage_lower_bound_pct")
    if enforce_coverage and coverage_pct is not None:
        grouped = df.groupby("department")
        contacts_by_dept = grouped["expected_contacts"].sum()
        pop_proxy_by_dept = grouped["reach_cap_population_proxy"].max()
        for dept in contacts_by_dept.index:
            floor = float(coverage_pct) * float(pop_proxy_by_dept[dept])
            actual = float(contacts_by_dept[dept])
            # Small epsilon: post-solve cent truncation rounds spend down.
            if actual < floor * (1.0 - 1e-3):
                errors.append(
                    f"coverage: {dept} expected_contacts {actual:.1f} "
                    f"< {float(coverage_pct):.0%} of population proxy ({floor:.1f})"
                )

    if errors:
        raise ValueError("allocation_output gate failed: " + "; ".join(errors))

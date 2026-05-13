"""Hard gates for ``allocation_output`` contract (Module B post-solve)."""

from __future__ import annotations

from typing import Final, cast

import pandas as pd

from module_b_resource_allocation.constants import (
    ALLOCATION_ROWS,
    CHANNEL_NAMES,
    DEPARTMENTS,
    WEEK_COUNT,
)

_SOLVER_OK: Final[tuple[str, ...]] = ("OPTIMAL", "FEASIBLE")


def validate_allocation_output_df(df: pd.DataFrame) -> None:
    """Validate ``df`` against the ``allocation_output`` schema contract.

    Args:
        df: Post-solve allocation table emitted by :func:`solve`.

    Returns:
        ``None`` when all gates pass.

    Raises:
        ValueError: If row counts, keys, statuses, or canonical labels are invalid.

    Example:
        ``validate_allocation_output_df(result.allocation)`` at the end of the CLI pipeline.
    """
    errors: list[str] = []
    if len(df) != ALLOCATION_ROWS:
        errors.append(f"row_count: expected {ALLOCATION_ROWS}, got {len(df)}")
    if df.duplicated(["department", "channel", "week_index"]).any():
        errors.append("unique_key: duplicate (department, channel, week_index)")
    bad_status = df[~df["solver_status"].isin(_SOLVER_OK)]
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
    if errors:
        raise ValueError("allocation_output gate failed: " + "; ".join(errors))

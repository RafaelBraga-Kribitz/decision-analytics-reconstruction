"""REF / RETAIL tier spread model for Module B FX layer (Phase 5).

The retail rate equals BCP reference plus a positive Δ_spread:
    TC_RETAIL(t) = TC_REF(t) * (1 + spread_pct(t))

Default spread is loaded from ``config/fx_retail_spread_prior.yaml``.
The per-week ``series_b_weekly`` key is used when a weekly DataFrame is
provided; ``series_a_monthly`` is available for monthly aggregations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd
import yaml

_CONFIG_DIR: Final[Path] = Path(__file__).resolve().parents[3] / "config"
_SPREAD_FILE: Final[Path] = _CONFIG_DIR / "fx_retail_spread_prior.yaml"

DEFAULT_SPREAD_PYG_PER_USD: Final[float] = 50.0


def load_spread_config(path: Path | None = None) -> dict:
    """Load the retail spread YAML used by :func:`apply_retail_spread`.

    Args:
        path: Optional override for the spread prior file location.

    Returns:
        Parsed YAML dict (for example containing ``series_b_weekly``).

    Raises:
        OSError: If the YAML file cannot be read.
        yaml.YAMLError: If the file contents are not valid YAML.

    Example:
        ``load_spread_config()`` before building the daily retail curve.
    """
    cfg_path = path or _SPREAD_FILE
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def apply_retail_spread(
    daily_df: pd.DataFrame,
    spread_cfg: dict | None = None,
    spread_pct_override: float | None = None,
) -> pd.DataFrame:
    """Add a ``tc_retail`` column to a daily TC_Ref DataFrame.

    The retail rate per week is: ``TC_REF * (1 + spread_pct_for_week)``.
    If ``spread_pct_override`` is given, that constant is used for all rows.
    Otherwise, the weekly spread is looked up from ``spread_cfg["series_b_weekly"]``.

    Falls back to ``DEFAULT_SPREAD_PYG_PER_USD / TC_REF`` (absolute PYG add-on)
    if no percentage entry is found for a given week.

    Parameters
    ----------
    daily_df:
        DataFrame returned by ``build_daily_series()``; must have ``date``,
        ``iso_week``, and ``tc_ref`` columns.
    spread_cfg:
        Loaded spread YAML dict (``load_spread_config()``).  If None, loaded
        from the default prior file.
    spread_pct_override:
        Constant fractional spread, e.g. ``0.009`` for ≈50 PYG/USD at 5 550.

    Returns
    -------
    pd.DataFrame
        Input DataFrame with an added ``tc_retail`` column.

    Raises
    ------
    KeyError
        If ``daily_df`` lacks ``date``, ``iso_week``, or ``tc_ref`` columns.

    Examples
    --------
    ``apply_retail_spread(build_daily_series(), load_spread_config())`` as used in the module
    docstring smoke test.
    """
    df = daily_df.copy()
    if spread_cfg is None:
        spread_cfg = load_spread_config()

    weekly_pct: dict[str, float] = spread_cfg.get("series_b_weekly", {})

    def _spread_for_row(row: pd.Series) -> float:  # type: ignore[type-arg]  # pandas stubs require type param; apply callback uses unparameterized Series
        if spread_pct_override is not None:
            return float(spread_pct_override)
        pct = weekly_pct.get(str(row["iso_week"]))
        if pct is not None:
            return float(pct)
        # fallback: absolute add-on as fraction
        return DEFAULT_SPREAD_PYG_PER_USD / float(row["tc_ref"])

    df["tc_retail"] = df.apply(
        lambda row: row["tc_ref"] * (1.0 + _spread_for_row(row)), axis=1
    ).astype(float)

    return df

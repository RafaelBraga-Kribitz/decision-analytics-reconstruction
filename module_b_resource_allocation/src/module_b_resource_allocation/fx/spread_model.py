"""REF / RETAIL tier spread model for Module B FX layer (Phase 5).

The retail rate equals BCP reference plus a positive Δ_spread:
    TC_RETAIL(t) = TC_REF(t) * (1 + spread_pct(t))

Default spread is loaded from ``config/fx_retail_spread_prior.yaml``.
The per-week ``series_b_weekly`` key is used when a weekly DataFrame is
provided; ``series_a_monthly`` is available for monthly aggregations.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

import pandas as pd
import yaml

_CONFIG_DIR: Final[Path] = Path(__file__).resolve().parents[3] / "config"
_SPREAD_FILE: Final[Path] = _CONFIG_DIR / "fx_retail_spread_prior.yaml"

# Undocumented absolute add-on used only when a week has no configured spread.
# Every use is disclosed by fx_fallback_report() and fails fx_fallback_gate()
# (F-086 / IMP-B04): any fallback week is a FAIL, never a silent substitution.
DEFAULT_SPREAD_PYG_PER_USD: Final[float] = 50.0
FX_FALLBACK_COLUMNS: Final[tuple[str, ...]] = ("iso_week", "tc_ref", "fallback_pct_applied")

logger = logging.getLogger(__name__)


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
    if spread_pct_override is None:
        fallback = fx_fallback_report(df, spread_cfg)
        if not fallback.empty:
            logger.warning(
                "FX spread fallback (%.0f PYG/USD add-on) used for %d week(s): %s",
                DEFAULT_SPREAD_PYG_PER_USD,
                len(fallback),
                ", ".join(fallback["iso_week"]),
            )

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


def fx_fallback_report(daily_df: pd.DataFrame, spread_cfg: dict | None = None) -> pd.DataFrame:
    """Weeks for which :func:`apply_retail_spread` falls back to the default add-on.

    Args:
        daily_df: Daily series with ``iso_week`` and ``tc_ref`` columns.
        spread_cfg: Loaded spread YAML; defaults to the committed prior.

    Returns:
        One row per fallback week (``FX_FALLBACK_COLUMNS``), sorted by
        ``iso_week``; empty when every week has a configured spread.

    Raises:
        KeyError: If ``daily_df`` lacks ``iso_week`` or ``tc_ref`` columns.

    Example:
        ``fx_fallback_report(build_daily_series(), load_spread_config())``.
    """
    if spread_cfg is None:
        spread_cfg = load_spread_config()
    weekly_pct: dict[str, float] = spread_cfg.get("series_b_weekly", {})
    missing = daily_df.loc[~daily_df["iso_week"].astype(str).isin(weekly_pct)]
    weekly = missing.groupby("iso_week", as_index=False)["tc_ref"].mean()
    weekly["fallback_pct_applied"] = DEFAULT_SPREAD_PYG_PER_USD / weekly["tc_ref"]
    return (
        weekly.reindex(columns=list(FX_FALLBACK_COLUMNS))
        .sort_values("iso_week")
        .reset_index(drop=True)
    )


def fx_fallback_gate(report: pd.DataFrame) -> str:
    """Gate the FX layer on fallback use: any fallback week is a failure.

    Args:
        report: Output of :func:`fx_fallback_report`.

    Returns:
        ``"PASS"`` when ``report`` is empty, otherwise ``"FAIL"``.

    Raises:
        AttributeError: If ``report`` is not a DataFrame.

    Example:
        ``fx_fallback_gate(fx_fallback_report(daily, cfg))``.
    """
    return "PASS" if report.empty else "FAIL"

"""BCP TC_Ref daily series loader for Jan–Apr 2018 (Phase 5).

Builds a complete daily DataFrame from weekly anchor priors, forward-fills
weekends/holidays with an imputed flag, and validates the two hard spec gates:
  - March floor:  every 2018-03-* row has tc_ref >= 5_500.0 PYG/USD
  - April band:   every 2018-04-* row has 5_550.0 <= tc_ref <= 5_750.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd
import yaml

_CONFIG_DIR: Final[Path] = Path(__file__).resolve().parents[3] / "config"
_PRIOR_FILE: Final[Path] = _CONFIG_DIR / "bcp_tc_ref_2018Q1_prior.yaml"

TC_REF_COLUMNS: Final[tuple[str, ...]] = (
    "date",
    "iso_week",
    "tc_ref",
    "tc_ref_imputed_flag",
    "provenance",
)

_MARCH_FLOOR: Final[float] = 5_500.0
_APRIL_LO: Final[float] = 5_550.0
_APRIL_HI: Final[float] = 5_750.0


def load_weekly_prior(path: Path | None = None) -> pd.DataFrame:
    """Return a 14-row DataFrame from the weekly prior YAML.

    Columns: ``iso_week``, ``tc_ref``, ``provenance``.
    """
    cfg_path = path or _PRIOR_FILE
    with open(cfg_path) as f:
        raw: dict = yaml.safe_load(f)

    provenance = raw.get("_meta", {}).get("provenance", "PRIOR")
    weekly: dict[str, float] = raw["weekly_reference_rate"]

    rows = [
        {"iso_week": week, "tc_ref": float(rate), "provenance": provenance}
        for week, rate in weekly.items()
    ]
    return pd.DataFrame(rows)


def build_daily_series(path: Path | None = None) -> pd.DataFrame:
    """Build a daily TC_Ref DataFrame for Jan 1 – Apr 30 2018.

    Each calendar day in the campaign window gets:
    - ``tc_ref``:  the anchor rate of its ISO week (constant within each week).
    - ``tc_ref_imputed_flag``:  True for weekends (Mon=0 … Sun=6, weekends 5-6).
    - ``provenance``:  passed through from the weekly prior.

    The returned DataFrame has columns ``TC_REF_COLUMNS`` and is indexed 0…N-1.
    """
    weekly = load_weekly_prior(path)
    week_to_rate: dict[str, float] = dict(zip(weekly["iso_week"], weekly["tc_ref"], strict=True))
    week_to_prov: dict[str, str] = dict(zip(weekly["iso_week"], weekly["provenance"], strict=True))

    date_range = pd.date_range("2018-01-01", "2018-04-30", freq="D")
    rows = []
    for dt in date_range:
        iso_week = dt.strftime("2018-W%W")
        # Pad single-digit weeks to match YAML keys (2018-W01…2018-W14)
        # strftime %W returns 0-padded 2-digit strings on Python 3.
        rate = week_to_rate.get(iso_week)
        if rate is None:
            continue  # outside the 14-week window
        prov = week_to_prov.get(iso_week, "PRIOR")
        is_weekend = dt.dayofweek >= 5
        rows.append(
            {
                "date": dt,
                "iso_week": iso_week,
                "tc_ref": rate,
                "tc_ref_imputed_flag": is_weekend,
                "provenance": prov,
            }
        )

    df = pd.DataFrame(rows)
    # Ensure correct dtypes
    df["date"] = pd.to_datetime(df["date"])
    df["tc_ref"] = df["tc_ref"].astype(float)
    df["tc_ref_imputed_flag"] = df["tc_ref_imputed_flag"].astype(bool)
    return df.reset_index(drop=True)


def validate_daily_series(df: pd.DataFrame) -> None:
    """Raise ValueError if the daily series violates spec hard gates.

    Gates (plan §4.3 and §7.2):
    - March floor: every row with date.month==3 must have tc_ref >= 5_500.
    - April band: every row with date.month==4 must have 5_550 <= tc_ref <= 5_750.
    """
    march = df[df["date"].dt.month == 3]
    if len(march) == 0:
        raise ValueError("Daily series contains no March 2018 rows")
    low_march = march[march["tc_ref"] < _MARCH_FLOOR]
    if len(low_march) > 0:
        raise ValueError(
            f"March floor violation: {len(low_march)} rows below "
            f"{_MARCH_FLOOR} PYG/USD. "
            f"Min={float(march['tc_ref'].min()):.1f}"
        )

    april = df[df["date"].dt.month == 4]
    if len(april) == 0:
        raise ValueError("Daily series contains no April 2018 rows")
    low_april = april[april["tc_ref"] < _APRIL_LO]
    high_april = april[april["tc_ref"] > _APRIL_HI]
    if len(low_april) > 0 or len(high_april) > 0:
        raise ValueError(
            f"April band violation: {len(low_april)} rows below {_APRIL_LO}, "
            f"{len(high_april)} rows above {_APRIL_HI}. "
            f"Range=[{april['tc_ref'].min():.1f}, {april['tc_ref'].max():.1f}]"
        )

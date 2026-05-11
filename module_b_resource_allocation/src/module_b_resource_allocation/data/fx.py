"""Jan–Apr 2018 tiered FX layer.

Two-tier model:

* ``REF`` — BCP reference rate ``TC_ref(t)``, applied to institutional
  contracts settled at the official rate.
* ``RETAIL`` — retail premium ``TC_retail(t) = TC_ref(t) * (1 + s(t))``,
  applied to PYG-denominated street-vendor billings (radio, billboards,
  field ops, sound cars).

Each ``s(t)`` is sourced from one of two independent priors:

* Series A — monthly retail spread anchors.
* Series B — weekly retail spread anchors.

The two series MUST NOT be combined within a single LP run; a run uses one
series and stamps it in provenance.  This module is the single source of
truth for FX conversion across Module B.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import pandas as pd
import yaml

from module_b_resource_allocation.constants import (
    BCP_CORRIDOR_MAX_PCT,
    FX_BAND_MAX_PCT_VS_BCP,
    WEEK_LABELS,
)

SeriesId = Literal["series_a_monthly", "series_b_weekly"]
FxTier = Literal["REF", "RETAIL"]


_DEFAULT_BCP_PATH: Final[Path] = (
    Path(__file__).resolve().parents[3] / "config" / "bcp_tc_ref_2018Q1_prior.yaml"
)
_DEFAULT_SPREAD_PATH: Final[Path] = (
    Path(__file__).resolve().parents[3] / "config" / "fx_retail_spread_prior.yaml"
)


@dataclass(frozen=True)
class FxLayer:
    """Resolved per-week FX rates for one (series, tier) combination."""

    series_id: SeriesId
    ref_by_week: dict[str, float]  # iso_week -> PYG per USD (reference)
    retail_by_week: dict[str, float]  # iso_week -> PYG per USD (retail)
    spread_by_week: dict[str, float]  # iso_week -> retail spread fraction

    def rate(self, iso_week: str, tier: FxTier) -> float:
        try:
            return self.ref_by_week[iso_week] if tier == "REF" else self.retail_by_week[iso_week]
        except KeyError as e:
            raise KeyError(f"FxLayer: unknown iso_week {iso_week!r}") from e

    def to_usd(self, amount_native: float, currency: str, iso_week: str, tier: FxTier) -> float:
        if currency == "USD":
            return float(amount_native)
        if currency == "PYG":
            return float(amount_native) / float(self.rate(iso_week, tier))
        raise ValueError(f"FxLayer.to_usd: unsupported currency {currency!r}")

    def to_pyg(self, amount_native: float, currency: str, iso_week: str, tier: FxTier) -> float:
        if currency == "PYG":
            return float(amount_native)
        if currency == "USD":
            return float(amount_native) * float(self.rate(iso_week, tier))
        raise ValueError(f"FxLayer.to_pyg: unsupported currency {currency!r}")


def _monthly_to_weekly(monthly: dict[str, float]) -> dict[str, float]:
    """Project monthly spreads onto the 14 ISO weeks for Jan–Apr 2018.

    Anchor weeks per month follow the campaign window:

    * Jan: W01–W04
    * Feb: W05–W08
    * Mar: W09–W13
    * Apr: W14
    """
    layout: list[tuple[str, list[str]]] = [
        ("2018-01", ["2018-W01", "2018-W02", "2018-W03", "2018-W04"]),
        ("2018-02", ["2018-W05", "2018-W06", "2018-W07", "2018-W08"]),
        ("2018-03", ["2018-W09", "2018-W10", "2018-W11", "2018-W12", "2018-W13"]),
        ("2018-04", ["2018-W14"]),
    ]
    out: dict[str, float] = {}
    for month, weeks in layout:
        if month not in monthly:
            raise KeyError(f"Series A spread missing month {month}")
        for w in weeks:
            out[w] = float(monthly[month])
    return out


def load_fx_layer(
    series_id: SeriesId = "series_b_weekly",
    bcp_path: Path | None = None,
    spread_path: Path | None = None,
) -> FxLayer:
    bcp_path = bcp_path or _DEFAULT_BCP_PATH
    spread_path = spread_path or _DEFAULT_SPREAD_PATH

    with open(bcp_path) as f:
        bcp_payload = yaml.safe_load(f)
    with open(spread_path) as f:
        spread_payload = yaml.safe_load(f)

    ref_by_week = {k: float(v) for k, v in bcp_payload["weekly_reference_rate"].items()}

    if series_id == "series_a_monthly":
        spread_by_week = _monthly_to_weekly(spread_payload["series_a_monthly"])
    elif series_id == "series_b_weekly":
        spread_by_week = {k: float(v) for k, v in spread_payload["series_b_weekly"].items()}
    else:
        raise ValueError(f"Unknown FX series_id {series_id!r}")

    missing = set(WEEK_LABELS) - set(ref_by_week)
    if missing:
        raise ValueError(f"BCP reference series missing weeks: {sorted(missing)}")
    missing = set(WEEK_LABELS) - set(spread_by_week)
    if missing:
        raise ValueError(f"Spread series {series_id} missing weeks: {sorted(missing)}")

    retail_by_week = {w: ref_by_week[w] * (1.0 + spread_by_week[w]) for w in WEEK_LABELS}
    return FxLayer(
        series_id=series_id,
        ref_by_week=ref_by_week,
        retail_by_week=retail_by_week,
        spread_by_week=spread_by_week,
    )


def fx_layer_to_frame(layer: FxLayer) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "iso_week": list(WEEK_LABELS),
            "series_id": [layer.series_id] * len(WEEK_LABELS),
            "tc_ref_pyg_per_usd": [layer.ref_by_week[w] for w in WEEK_LABELS],
            "retail_spread_pct": [layer.spread_by_week[w] for w in WEEK_LABELS],
            "tc_retail_pyg_per_usd": [layer.retail_by_week[w] for w in WEEK_LABELS],
        }
    )


def enforce_bcp_corridor(layer: FxLayer, max_pct: float = BCP_CORRIDOR_MAX_PCT) -> None:
    """Raise ValueError if any reference rate moves > ``max_pct`` week over week."""
    ref = [layer.ref_by_week[w] for w in WEEK_LABELS]
    for i in range(1, len(ref)):
        delta = abs(ref[i] - ref[i - 1]) / ref[i - 1]
        if delta > max_pct:
            raise ValueError(
                f"BCP reference rate week-over-week jump exceeds corridor: "
                f"{WEEK_LABELS[i-1]} → {WEEK_LABELS[i]} = {delta:.4f} > {max_pct:.4f}"
            )


def enforce_fx_band(layer: FxLayer, max_pct: float = FX_BAND_MAX_PCT_VS_BCP) -> None:
    """Validate that the retail rate doesn't undercut the reference rate.

    ``max_pct`` is the allowed absolute deviation below the reference rate.
    Retail rates above the reference are always allowed (spreads are non-negative).
    """
    for w in WEEK_LABELS:
        deviation = (layer.retail_by_week[w] - layer.ref_by_week[w]) / layer.ref_by_week[w]
        if deviation < -max_pct:
            raise ValueError(
                f"FX retail rate undercuts reference at {w}: deviation={deviation:.4f}"
            )


def convert_budget_lines_to_usd(budget_lines: pd.DataFrame, layer: FxLayer) -> pd.DataFrame:
    """Return ``budget_lines`` with an added ``amount_usd`` column.

    Required input columns: ``currency``, ``amount_native``, ``iso_week``,
    ``fx_tier`` (each row chooses its own tier).
    """
    required = {"currency", "amount_native", "iso_week", "fx_tier"}
    missing = required - set(budget_lines.columns)
    if missing:
        raise KeyError(f"convert_budget_lines_to_usd: missing columns {sorted(missing)}")

    def _row_to_usd(row: pd.Series) -> float:
        return layer.to_usd(
            float(row["amount_native"]),
            str(row["currency"]),
            str(row["iso_week"]),
            str(row["fx_tier"]),  # type: ignore[arg-type]
        )

    out = budget_lines.copy()
    out["amount_usd"] = out.apply(_row_to_usd, axis=1)
    out["fx_series_id"] = layer.series_id
    return out

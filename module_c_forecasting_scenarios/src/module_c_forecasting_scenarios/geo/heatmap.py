"""Department-level battleground win probabilities (hierarchical partial-pooling from TSJE).

Replaces the fabricated ``0.12 * (last − 3.8) + noise`` formula (v0.1) with a
calibrated model derived from the official 2018 TSJE per-department presidential
results (``geo/tsje_2018_department_results.csv``, shipped as package data; GATE:
PASS against the verified national totals of 1,206,067 / 1,110,464):

  1. Load TSJE candidate vote counts per department.
  2. Compute each department's candidate-margin *swing factor* relative to the
     national candidate total.
  3. Given the tracking model's last-day national posterior (mean + 94% HDI),
     propagate uncertainty through the swing model and convert to P(Abdo wins)
     via the Gaussian CDF.

Sign convention (inherits from tracking model): positive margin = Candidate A
(Abdo/ANR) leads; negative margin = GANAR/Alegre leads.
win_probability_a = P(Candidate A / Abdo wins the department).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
from module_b_resource_allocation.constants import DEPARTMENTS
from scipy.stats import norm

from module_c_forecasting_scenarios.config import load_sampler_config
from module_c_forecasting_scenarios.data.contract_validate import validate_dataframe_contract

MODEL_VERSION = "c_battleground_v0.2"

# Idiosyncratic per-department uncertainty (pp). Sets a floor on each dept HDI
# width so that near-the-margin departments are not called as near-certain when
# the tracking posterior alone is narrow — justified by unmodelled local factors
# (candidate strength, local issues, ground game). Value calibrated to give
# ~15–20 pp HDI width for swing departments at typical national posterior widths.
_SIGMA_IDIO_PP: float = 1.5

# Loaded from pymc_sampler.yaml for sync with tracking model (0.94 = 94% HDI).
_HDI_PROB: float = float(load_sampler_config().get("hdi_prob", 0.94))
# Two-sided z-score for HDI: norm.ppf(1 − (1−hdi_prob)/2)
_HDI_Z: float = float(norm.ppf(1.0 - (1.0 - _HDI_PROB) / 2.0))

_DEPT_POLYGONS_PATH = Path(__file__).parent / "paraguay_departments.geojson"
# Shipped as package data alongside the polygons so it resolves under every install
# mode (editable, wheel, Docker) — a repo-root path would vanish once installed.
_TSJE_CSV = Path(__file__).parent / "tsje_2018_department_results.csv"


def _load_department_polygons() -> dict[str, Any]:
    """Return mapping department_name → GeoJSON geometry dict."""
    geo = json.loads(_DEPT_POLYGONS_PATH.read_text())
    return {f["properties"]["department"]: f["geometry"] for f in geo["features"]}


def _load_tsje() -> pd.DataFrame:
    """Load and validate the TSJE 2018 per-department results CSV."""
    if not _TSJE_CSV.exists():
        raise FileNotFoundError(
            f"TSJE department results not found: {_TSJE_CSV}\n"
            "Expected as geo package data (geo/tsje_2018_department_results.csv)."
        )
    df = pd.read_csv(_TSJE_CSV)
    required = {"department_ascii", "abdo_anr_votes", "alegre_ganar_votes"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"TSJE CSV missing columns: {missing}")
    df["abdo_anr_votes"] = df["abdo_anr_votes"].astype(int)
    df["alegre_ganar_votes"] = df["alegre_ganar_votes"].astype(int)
    return df


def _swing_factors(df: pd.DataFrame) -> dict[str, float]:
    """Compute per-department candidate-margin swing factors relative to national.

    swing_j = dept_candidate_margin_j / national_candidate_margin

    where dept_candidate_margin = (abdo − ganar) / (abdo + ganar) × 100 pp.
    Positive swing → dept moves with Abdo; negative → dept is a GANAR stronghold.
    """
    df = df.copy()
    df["cand_total"] = df["abdo_anr_votes"] + df["alegre_ganar_votes"]
    df["dept_margin_pp"] = (
        (df["abdo_anr_votes"] - df["alegre_ganar_votes"]) / df["cand_total"] * 100.0
    )
    nat_abdo = df["abdo_anr_votes"].sum()
    nat_ganar = df["alegre_ganar_votes"].sum()
    nat_margin_pp = (nat_abdo - nat_ganar) / (nat_abdo + nat_ganar) * 100.0
    df["swing"] = df["dept_margin_pp"] / nat_margin_pp
    return dict(zip(df["department_ascii"], df["swing"], strict=True))


def export_battleground_department_table(
    daily_forecast: pd.DataFrame,
    out_path: Path,
    *,
    calibration_series: str,
) -> pd.DataFrame:
    """Map last-day tracking posterior to per-department win probability.

    Uses a calibrated hierarchical model (v0.2):
      • Each department's margin tracks the national margin linearly via its
        TSJE-derived swing factor (partial pooling toward the national result).
      • National posterior uncertainty propagates through the swing factor;
        idiosyncratic noise (_SIGMA_IDIO_PP = 1.5 pp) is added in quadrature.
      • win_probability_a = P(Abdo/Candidate A wins dept j) = Φ(m_dept / σ_dept).

    Writes three outputs alongside out_path:
    - ``{stem}.parquet``  — contract-validated 4-column table
    - ``{stem}.geojson``  — null-geometry GeoJSON (backward compat)
    - ``battleground_probability_heatmap.geojson`` — polygon choropleth
    """
    df_fc = daily_forecast.sort_values("date")
    last = df_fc.iloc[-1]

    m_pp = float(last["posterior_mean_preference_margin_pp"])
    hdi_lo = float(last.get("posterior_hdi_low_pp", m_pp - 2.0))  # type: ignore[arg-type]
    hdi_hi = float(last.get("posterior_hdi_high_pp", m_pp + 2.0))  # type: ignore[arg-type]
    # National posterior standard deviation estimated from 94% HDI width.
    sigma_national = (hdi_hi - hdi_lo) / (2.0 * _HDI_Z)

    tsje = _load_tsje()
    swings = _swing_factors(tsje)

    rows: list[dict[str, Any]] = []
    for dept in DEPARTMENTS:
        swing = swings.get(dept, 0.0)
        dept_m = swing * m_pp
        # Uncertainty: national variance amplified by swing, plus idiosyncratic floor.
        sigma_dept = float(np.sqrt((swing * sigma_national) ** 2 + _SIGMA_IDIO_PP**2))
        # P(Abdo wins dept j) = P(dept_margin > 0) = Φ(dept_m / σ_dept)
        win_prob_a = float(norm.cdf(dept_m / sigma_dept))
        # Choropleth HDI: scenario bounds on win_prob at the 94% HDI limits of the
        # national margin (not a posterior HDI on win_prob itself, but interpretable
        # as the range of plausible win probabilities under the national posterior).
        wp_at_nat_lo = float(norm.cdf(swing * hdi_lo / sigma_dept))
        wp_at_nat_hi = float(norm.cdf(swing * hdi_hi / sigma_dept))
        rows.append(
            {
                "department": dept,
                "calibration_series": calibration_series,
                "win_probability_a": win_prob_a,
                "model_version": MODEL_VERSION,
                "_posterior_win_prob": win_prob_a,
                "_hdi_low": min(wp_at_nat_lo, wp_at_nat_hi),
                "_hdi_high": max(wp_at_nat_lo, wp_at_nat_hi),
            }
        )

    full = pd.DataFrame(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    contract_cols = ["department", "calibration_series", "win_probability_a", "model_version"]
    out = cast(pd.DataFrame, full[contract_cols].copy())
    validate_dataframe_contract(out, "battleground_department_probability")
    out.to_parquet(out_path, index=False)

    null_features: list[dict[str, Any]] = [
        {
            "type": "Feature",
            "properties": {
                "department": r["department"],
                "win_probability_a": r["win_probability_a"],
                "calibration_series": calibration_series,
            },
            "geometry": None,
        }
        for _, r in out.iterrows()
    ]
    out_path.with_suffix(".geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": null_features})
    )

    dept_polys = _load_department_polygons()
    heatmap_features: list[dict[str, Any]] = [
        {
            "type": "Feature",
            "properties": {
                "department": str(r["department"]),
                "posterior_win_prob": float(r["_posterior_win_prob"]),
                "hdi_low": float(r["_hdi_low"]),
                "hdi_high": float(r["_hdi_high"]),
                "calibration_series": calibration_series,
            },
            "geometry": dept_polys.get(str(r["department"])),
        }
        for _, r in full.iterrows()
    ]
    heatmap_path = out_path.parent / "battleground_probability_heatmap.geojson"
    heatmap_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": heatmap_features}, indent=2)
    )

    return out

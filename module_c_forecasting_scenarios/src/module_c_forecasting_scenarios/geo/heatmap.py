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

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
from module_b_resource_allocation.constants import DEPARTMENTS
from scipy.stats import norm

from module_c_forecasting_scenarios.config import load_sampler_config
from module_c_forecasting_scenarios.data.contract_validate import validate_dataframe_contract

MODEL_VERSION = "c_battleground_v0.3"

# Idiosyncratic per-department uncertainty (pp): a floor on each department's
# margin dispersion representing unmodelled local factors (candidate strength,
# local issues, ground game).
#
# PROVENANCE — illustrative assumption (IMP-C05 / issue #63): this value is
# NOT estimated from data. Estimating it would require department-level
# poll-vs-result residuals across elections; this reconstruction carries only
# national tracking polls plus the single realized 2018 department table the
# swing factors are derived from (their in-sample residual is zero by
# construction, so it cannot identify this parameter). Per the IMP-C05 spec's
# fallback, the parameter and every artifact it touches are therefore labeled
# ``illustrative`` in the schema contract and report captions. Do not justify
# a new value by a target visual property ("gives ~X pp width") — either
# derive it from a documented reference or keep the illustrative label.
_SIGMA_IDIO_PP: float = 1.5
_SIGMA_IDIO_PROVENANCE = "illustrative_assumption_not_estimated"

# The estimand of every battleground artifact: outcome data enters twice —
# (1) the national posterior is softly anchored to the verified outcome
# (config/calibration.yaml use_outcome_anchor) and (2) the swing factors are
# derived from the realized TSJE department results. The schema contract and
# report captions must carry this disclosure (F-078 recurrence invariant).
_ESTIMAND_ANCHORED = "retrodiction"
_ESTIMAND_UNANCHORED = "unanchored_retrodiction"

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
    anchored: bool = True,
) -> pd.DataFrame:
    """Map last-day tracking posterior to per-department win probability.

    Uses a calibrated hierarchical model (v0.3):
      • Each department's margin tracks the national margin linearly via its
        TSJE-derived swing factor (partial pooling toward the national result).
      • National posterior uncertainty propagates through the swing factor;
        idiosyncratic noise (``_SIGMA_IDIO_PP``, an illustrative assumption —
        see its provenance comment) is added in quadrature.
      • win_probability_a = P(Abdo/Candidate A wins dept j) = Φ(m_dept / σ_dept).

    Args:
        daily_forecast: Daily posterior frame; the last row's mean/HDI drive
            the mapping.
        out_path: Destination parquet path (siblings written alongside).
        calibration_series: Active calibration series label (``A``/``B``).
        anchored: Whether ``daily_forecast`` came from an outcome-anchored
            tracking fit. Controls the exported ``estimand`` label
            (``retrodiction`` vs ``unanchored_retrodiction`` — the swing
            factors are outcome-derived either way) and the manifest.

    Returns:
        The contract-validated table that was written.

    Raises:
        QAGateFailure: If the exported frame violates the schema contract.
        AssertionError: If any row violates
            ``0 <= hdi_low <= win_probability_a <= hdi_high <= 1``.

    Writes four outputs alongside out_path:
    - ``{stem}.parquet``  — contract-validated table (incl. estimand + HDI)
    - ``{stem}.geojson``  — null-geometry GeoJSON (backward compat)
    - ``battleground_probability_heatmap.geojson`` — polygon choropleth
    - ``{stem}_manifest.json`` — sigma provenance, hdi_prob, input hash
    """
    df_fc = daily_forecast.sort_values("date")
    last = df_fc.iloc[-1]
    estimand = _ESTIMAND_ANCHORED if anchored else _ESTIMAND_UNANCHORED

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
                "estimand": estimand,
                "hdi_low": min(wp_at_nat_lo, wp_at_nat_hi),
                "hdi_high": max(wp_at_nat_lo, wp_at_nat_hi),
                "_posterior_win_prob": win_prob_a,
                "_hdi_low": min(wp_at_nat_lo, wp_at_nat_hi),
                "_hdi_high": max(wp_at_nat_lo, wp_at_nat_hi),
            }
        )

    full = pd.DataFrame(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    contract_cols = [
        "department",
        "calibration_series",
        "win_probability_a",
        "model_version",
        "estimand",
        "hdi_low",
        "hdi_high",
    ]
    out = cast(pd.DataFrame, full[contract_cols].copy())
    # False-precision guard (IMP-C05 NFR): every exported row carries an
    # interval that brackets its point estimate, all in [0, 1]. Violations
    # abort the export before anything is written.
    assert bool(
        (
            (out["hdi_low"] >= 0.0)
            & (out["hdi_low"] <= out["win_probability_a"])
            & (out["win_probability_a"] <= out["hdi_high"])
            & (out["hdi_high"] <= 1.0)
        ).all()
    ), "battleground export violates 0 <= hdi_low <= win_probability_a <= hdi_high <= 1"
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

    if anchored:
        # The polygon choropleth keeps its stable filename and is only ever
        # the anchored run's view — the unanchored companion must not clobber
        # it (its table lives under its own stem).
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
                    "estimand": estimand,
                },
                "geometry": dept_polys.get(str(r["department"])),
            }
            for _, r in full.iterrows()
        ]
        heatmap_path = out_path.parent / "battleground_probability_heatmap.geojson"
        heatmap_path.write_text(
            json.dumps({"type": "FeatureCollection", "features": heatmap_features}, indent=2)
        )

    # Run manifest (IMP-C05 reproducibility NFR): records the sigma value and
    # its provenance, the HDI level, the estimand, and the hash of the swing
    # factors' input data.
    manifest = {
        "model_version": MODEL_VERSION,
        "estimand": estimand,
        "anchored_national_posterior": anchored,
        "sigma_idio_pp": _SIGMA_IDIO_PP,
        "sigma_idio_provenance": _SIGMA_IDIO_PROVENANCE,
        "hdi_prob": _HDI_PROB,
        "tsje_input_sha256": hashlib.sha256(_TSJE_CSV.read_bytes()).hexdigest(),
        "outcome_data_entry_points": [
            (
                "national posterior outcome anchor (config/calibration.yaml use_outcome_anchor)"
                if anchored
                else "none at the national layer (unanchored companion run)"
            ),
            "swing factors derived from realized tsje_2018_department_results.csv",
        ],
    }
    manifest_path = out_path.parent / f"{out_path.stem}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    return out


def write_anchor_comparison(
    anchored_table: pd.DataFrame,
    unanchored_table: pd.DataFrame,
    out_path: Path,
) -> pd.DataFrame:
    """Publish the anchored-vs-unanchored companion comparison with flip list.

    Args:
        anchored_table: Contract table from the anchored run.
        unanchored_table: Contract table from the unanchored companion run.
        out_path: Destination markdown path for the comparison artifact.

    Returns:
        Per-department comparison frame (anchored/unanchored probabilities,
        classification flip flag).

    Raises:
        ValueError: If the two tables are numerically identical — the
            "unanchored" run silently consumed the anchor (IMP-C05 negative
            constraint), or if department sets differ.

    Example:
        ``write_anchor_comparison(anchored, unanchored, Path("cmp.md"))``
    """
    a = anchored_table.set_index("department")["win_probability_a"]
    u = unanchored_table.set_index("department")["win_probability_a"]
    if set(a.index) != set(u.index):
        raise ValueError("anchored and unanchored tables cover different departments")
    u = u.reindex(a.index)
    if bool(np.allclose(a.to_numpy(), u.to_numpy())):
        raise ValueError(
            "anchored and unanchored battleground tables are numerically identical — "
            "the companion run silently consumed the outcome anchor (IMP-C05)"
        )
    cmp_df = pd.DataFrame(
        {
            "department": a.index,
            "win_probability_a_anchored": a.to_numpy(),
            "win_probability_a_unanchored": u.to_numpy(),
        }
    )
    cmp_df["classification_flip"] = (cmp_df["win_probability_a_anchored"] > 0.5) != (
        cmp_df["win_probability_a_unanchored"] > 0.5
    )
    flips = cmp_df[cmp_df["classification_flip"]]["department"].tolist()

    lines = [
        "# Battleground anchored vs unanchored companion",
        "",
        "The anchored table is a **retrodiction** (outcome-anchored national posterior x "
        "outcome-derived swing factors). The companion below re-runs the tracking fit with "
        "`use_outcome_anchor: false`; swing factors remain outcome-derived in both, so "
        "neither column is an out-of-sample forecast.",
        "",
        f"Departments whose >0.5 classification flips: " f"{', '.join(flips) if flips else 'none'}",
        "",
        "| Department | anchored P(A) | unanchored P(A) | flip |",
        "|---|---|---|---|",
    ]
    for _, r in cmp_df.sort_values("department").iterrows():
        lines.append(
            f"| {r['department']} | {r['win_probability_a_anchored']:.3f} "
            f"| {r['win_probability_a_unanchored']:.3f} "
            f"| {'YES' if bool(r['classification_flip']) else ''} |"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")
    return cmp_df

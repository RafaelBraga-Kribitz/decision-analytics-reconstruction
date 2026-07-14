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
from module_c_forecasting_scenarios.geo.sigma_estimator import (
    load_sigma_manifest_extras,
    load_sigma_yaml,
)

MODEL_VERSION = "c_battleground_v0.5"

# Fallback when sigma yaml is unavailable (tests / minimal installs).
_SIGMA_IDIO_PP_FALLBACK: float = 1.5
_SIGMA_IDIO_PROVENANCE_FALLBACK = "illustrative_assumption_not_estimated"

_sigma_idio_by_dept: dict[str, float] | None = None
_sigma_manifest_extras: dict[str, Any] | None = None

# Primary published estimand: poll-implied win probabilities from an unanchored
# national posterior × TSJE-derived swing factors (swing still outcome-derived).
_ESTIMAND_POLL_IMPLIED = "poll_implied"
# Secondary diagnostic: outcome-anchored national posterior × same swing factors —
# outcome data enters twice (F-078); not for decision support.
_ESTIMAND_RETRODICTION = "retrodiction"

# Grid size for percentile HDI on win_prob (propagate national margin uncertainty).
_HDI_GRID_N = 201

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


def _resolve_sigma_idio(sigma_yaml_path: Path | None = None) -> dict[str, float]:
    global _sigma_idio_by_dept, _sigma_manifest_extras
    try:
        if sigma_yaml_path is not None:
            by_dept = load_sigma_yaml(sigma_yaml_path)
            extras = load_sigma_manifest_extras(sigma_yaml_path)
        else:
            by_dept = load_sigma_yaml()
            extras = load_sigma_manifest_extras()
    except (FileNotFoundError, OSError):
        by_dept = {d: _SIGMA_IDIO_PP_FALLBACK for d in DEPARTMENTS}
        extras = {
            "sigma_idio_provenance": _SIGMA_IDIO_PROVENANCE_FALLBACK,
            "sigma_estimator_version": None,
            "reference_data_sha256": "",
            "sigma_floor_pp": _SIGMA_IDIO_PP_FALLBACK,
            "proxy_weight_scheme": {},
            "n_obs_per_department": {d: 0 for d in DEPARTMENTS},
            "sigma_idio_by_department": by_dept,
        }
    _sigma_idio_by_dept = by_dept
    _sigma_manifest_extras = extras
    return by_dept


def _sigma_dept_v05(sigma_national: float, sigma_idio_j: float) -> float:
    """v0.5: national uncertainty enters without swing scaling."""
    return float(np.sqrt(sigma_national**2 + sigma_idio_j**2))


def _win_prob_hdi(
    swing: float,
    m_pp: float,
    hdi_lo: float,
    hdi_hi: float,
    sigma_national: float,
    sigma_idio_j: float,
) -> tuple[float, float, float]:
    """Point estimate and percentile HDI on win_prob under national margin uncertainty.

    v0.5: μ_dept = swing × m; σ_dept = √(σ_national² + σ_idio,j²).
    """
    sigma_dept = _sigma_dept_v05(sigma_national, sigma_idio_j)
    lo = min(hdi_lo, hdi_hi)
    hi = max(hdi_lo, hdi_hi)
    m_grid = np.linspace(lo, hi, _HDI_GRID_N)
    if not np.any(np.isclose(m_grid, m_pp)):
        m_grid = np.sort(np.append(m_grid, m_pp))
    mu_grid = swing * m_grid
    wp_samples = norm.cdf(mu_grid / sigma_dept)
    alpha = (1.0 - _HDI_PROB) / 2.0
    hdi_low = float(np.quantile(wp_samples, alpha))
    hdi_high = float(np.quantile(wp_samples, 1.0 - alpha))
    win_prob = float(norm.cdf(swing * m_pp / sigma_dept))
    hdi_low = min(hdi_low, win_prob)
    hdi_high = max(hdi_high, win_prob)
    return win_prob, hdi_low, hdi_high


def _build_battleground_rows(
    swings: dict[str, float],
    m_pp: float,
    hdi_lo: float,
    hdi_hi: float,
    sigma_national: float,
    calibration_series: str,
    estimand: str,
    sigma_idio_by_dept: dict[str, float],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dept in DEPARTMENTS:
        swing = swings.get(dept, 0.0)
        sigma_idio_j = float(sigma_idio_by_dept.get(dept, _SIGMA_IDIO_PP_FALLBACK))
        win_prob_a, hdi_low, hdi_high = _win_prob_hdi(
            swing, m_pp, hdi_lo, hdi_hi, sigma_national, sigma_idio_j
        )
        rows.append(
            {
                "department": dept,
                "calibration_series": calibration_series,
                "win_probability_a": win_prob_a,
                "model_version": MODEL_VERSION,
                "estimand": estimand,
                "hdi_low": hdi_low,
                "hdi_high": hdi_high,
                "_posterior_win_prob": win_prob_a,
                "_hdi_low": hdi_low,
                "_hdi_high": hdi_high,
            }
        )
    return pd.DataFrame(rows)


def _assert_interval_brackets_point(out: pd.DataFrame) -> None:
    assert bool(
        (
            (out["hdi_low"] >= 0.0)
            & (out["hdi_low"] <= out["win_probability_a"])
            & (out["win_probability_a"] <= out["hdi_high"])
            & (out["hdi_high"] <= 1.0)
        ).all()
    ), "battleground export violates 0 <= hdi_low <= win_probability_a <= hdi_high <= 1"


def _write_null_geojson(out: pd.DataFrame, out_path: Path, calibration_series: str) -> None:
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


def _write_heatmap_geojson(
    full: pd.DataFrame,
    out_path: Path,
    calibration_series: str,
    estimand: str,
) -> None:
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


def _write_battleground_manifest(
    out_path: Path,
    *,
    estimand: str,
    anchored: bool,
    sigma_extras: dict[str, Any],
) -> None:
    manifest = {
        "model_version": MODEL_VERSION,
        "estimand": estimand,
        "anchored_national_posterior": anchored,
        "sigma_idio_provenance": sigma_extras.get(
            "sigma_idio_provenance", _SIGMA_IDIO_PROVENANCE_FALLBACK
        ),
        "sigma_estimator_version": sigma_extras.get("sigma_estimator_version"),
        "reference_data_sha256": sigma_extras.get("reference_data_sha256", ""),
        "sigma_floor_pp": sigma_extras.get("sigma_floor_pp"),
        "proxy_weight_scheme": sigma_extras.get("proxy_weight_scheme"),
        "n_obs_per_department": sigma_extras.get("n_obs_per_department"),
        "sigma_idio_by_department": sigma_extras.get("sigma_idio_by_department"),
        "mapping": "v0.5_decoupled_sigma",
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


def export_battleground_department_table(
    daily_forecast: pd.DataFrame,
    out_path: Path,
    *,
    calibration_series: str,
    anchored: bool = False,
    primary: bool = False,
    sigma_yaml_path: Path | None = None,
) -> pd.DataFrame:
    """Map last-day tracking posterior to per-department win probability.

    Uses a calibrated hierarchical model (v0.5):
      • μ_dept,j = swing_j × m_national (TSJE-derived swing factors).
      • σ_dept,j = √(σ_national² + σ_idio,j²) — swing does not amplify σ (F-081).
      • σ_idio,j estimated from reference poll residuals + election cross-section
        floor (``geo/sigma_estimator.py``), or illustrative fallback in tests.
      • win_probability_a = Φ(μ_dept / σ_dept).
      • HDI on win_prob uses percentile propagation over the national margin grid.

    Args:
        daily_forecast: Daily posterior frame; the last row's mean/HDI drive
            the mapping.
        out_path: Destination parquet path (siblings written alongside).
        calibration_series: Active calibration series label (``A``/``B``).
        anchored: Whether ``daily_forecast`` came from an outcome-anchored
            tracking fit. ``False`` → ``poll_implied`` (primary); ``True`` →
            ``retrodiction`` (diagnostic). Swing factors are outcome-derived
            either way.
        primary: When ``True``, write the polygon choropleth GeoJSON (only the
            primary poll_implied export should set this).
        sigma_yaml_path: Optional path to ``battleground_sigma_idio.yaml``.
            When omitted, loads from ``data/reference/battleground/``.

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
    estimand = _ESTIMAND_RETRODICTION if anchored else _ESTIMAND_POLL_IMPLIED

    m_pp = float(last["posterior_mean_preference_margin_pp"])
    hdi_lo = float(last.get("posterior_hdi_low_pp", m_pp - 2.0))  # type: ignore[arg-type]
    hdi_hi = float(last.get("posterior_hdi_high_pp", m_pp + 2.0))  # type: ignore[arg-type]
    # National posterior standard deviation estimated from 94% HDI width.
    sigma_national = (hdi_hi - hdi_lo) / (2.0 * _HDI_Z)

    sigma_idio_by_dept = _resolve_sigma_idio(sigma_yaml_path)
    sigma_extras = _sigma_manifest_extras or {}

    tsje = _load_tsje()
    swings = _swing_factors(tsje)
    full = _build_battleground_rows(
        swings,
        m_pp,
        hdi_lo,
        hdi_hi,
        sigma_national,
        calibration_series,
        estimand,
        sigma_idio_by_dept,
    )
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
    _assert_interval_brackets_point(out)
    validate_dataframe_contract(out, "battleground_department_probability")
    out.to_parquet(out_path, index=False)

    _write_null_geojson(out, out_path, calibration_series)
    if primary:
        _write_heatmap_geojson(full, out_path, calibration_series, estimand)
    _write_battleground_manifest(
        out_path, estimand=estimand, anchored=anchored, sigma_extras=sigma_extras
    )

    return out


def _comparison_table_rows(cmp_df: pd.DataFrame) -> list[str]:
    lines = [
        "| Department | poll-implied P(A) | retrodiction P(A) | flip |",
        "|---|---|---|---|",
    ]
    for _, r in cmp_df.sort_values("department").iterrows():
        lines.append(
            f"| {r['department']} | {r['win_probability_a_poll_implied']:.3f} "
            f"| {r['win_probability_a_retrodiction']:.3f} "
            f"| {'YES' if bool(r['classification_flip']) else ''} |"
        )
    return lines


def write_anchor_comparison(
    poll_implied_table: pd.DataFrame,
    retrodiction_table: pd.DataFrame,
    out_path: Path,
) -> pd.DataFrame:
    """Publish poll-implied vs retrodiction companion comparison with flip list.

    Args:
        poll_implied_table: Primary contract table (unanchored national posterior).
        retrodiction_table: Diagnostic table (outcome-anchored national posterior).
        out_path: Destination markdown path for the comparison artifact.

    Returns:
        Per-department comparison frame (poll-implied/retrodiction probabilities,
        classification flip flag).

    Raises:
        ValueError: If the two tables are numerically identical — the
            retrodiction run silently consumed the anchor (IMP-C05 negative
            constraint), or if department sets differ.

    Example:
        ``write_anchor_comparison(poll_implied, retrodiction, Path("cmp.md"))``
    """
    u = poll_implied_table.set_index("department")["win_probability_a"]
    a = retrodiction_table.set_index("department")["win_probability_a"]
    if set(a.index) != set(u.index):
        raise ValueError("poll_implied and retrodiction tables cover different departments")
    u = u.reindex(a.index)
    if bool(np.allclose(a.to_numpy(), u.to_numpy())):
        raise ValueError(
            "poll_implied and retrodiction battleground tables are numerically identical — "
            "the retrodiction run silently consumed the outcome anchor (IMP-C05)"
        )
    cmp_df = pd.DataFrame(
        {
            "department": a.index,
            "win_probability_a_poll_implied": u.to_numpy(),
            "win_probability_a_retrodiction": a.to_numpy(),
        }
    )
    cmp_df["classification_flip"] = (cmp_df["win_probability_a_poll_implied"] > 0.5) != (
        cmp_df["win_probability_a_retrodiction"] > 0.5
    )
    flips = cmp_df[cmp_df["classification_flip"]]["department"].tolist()

    lines = [
        "# Battleground poll-implied vs retrodiction companion",
        "",
        "The **poll-implied** column is the primary published view (unanchored national "
        "posterior × TSJE-derived swing factors). The **retrodiction** column is a "
        "calibration diagnostic (outcome-anchored national posterior × the same swing "
        "factors). Swing factors remain outcome-derived in both; neither column is an "
        "out-of-sample forecast.",
        "",
        f"Departments whose >0.5 classification flips: {', '.join(flips) if flips else 'none'}",
        "",
        *_comparison_table_rows(cmp_df),
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")
    return cmp_df

"""Hierarchical tracking model: latent daily margin random walk + pollster offsets."""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any, cast

import arviz as az
import numpy as np
import pandas as pd
import pymc as pm
import yaml

from module_c_forecasting_scenarios.paths import module_config_dir

MODEL_VERSION = "c_tracking_hierarchical_v0.3"  # v0.3: honest 94% HDI bands (az.hdi); v0.2 stored 5/95 quantiles under hdi names

# Probability mass of the credible interval stored in the ``*_hdi_*`` columns and
# labelled "94% HDI" on every figure. The bounds are a genuine highest-density
# interval (az.hdi), not 5/95 equal-tailed quantiles (the prior, mislabelled
# behaviour). Keep this in sync with the "94% HDI" titles in reports/eda.
HDI_PROB = 0.94
INTERVAL_TYPE = "HDI"


def _sampler_kwargs() -> dict[str, Any]:
    path = module_config_dir() / "pymc_sampler.yaml"
    with open(path) as f:
        cfg = yaml.safe_load(f)
    if os.environ.get("MC_FAST"):
        return {
            "chains": 2,
            "draws": int(cfg["draws_fast"]),
            "tune": int(cfg["tune_fast"]),
            "target_accept": float(cfg.get("target_accept", 0.9)),
            "random_seed": int(cfg.get("random_seed", 42)),
        }
    max_treedepth = int(cfg.get("max_treedepth", 10))
    return {
        "chains": int(cfg.get("chains", 4)),
        "draws": int(cfg.get("draws", 1000)),
        "tune": int(cfg.get("tune", 1000)),
        "target_accept": float(cfg.get("target_accept", 0.95)),
        "random_seed": int(cfg.get("random_seed", 42)),
        "nuts_sampler_kwargs": {"max_treedepth": max_treedepth},
    }


def _build_day_index(
    tracking: pd.DataFrame, outcome_event_date: date
) -> tuple[pd.DatetimeIndex, np.ndarray]:
    fs = pd.to_datetime(tracking["field_window_start"])
    fe = pd.to_datetime(tracking["field_window_end"])
    mid = fs + (fe - fs) / 2
    mid_dates = mid.dt.normalize().dt.date
    end = outcome_event_date - timedelta(days=1)
    start = min(mid_dates.min(), date(2017, 12, 1))
    days = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="D")
    day_to_i: dict[date, int] = {}
    for i in range(len(days)):
        d_i = pd.Timestamp(days[i]).date()  # type: ignore[arg-type]  # DatetimeIndex item; runtime is Timestamp-compatible
        day_to_i[d_i] = i
    start_d = pd.Timestamp(days[0]).date()  # type: ignore[arg-type]  # DatetimeIndex item; runtime is Timestamp-compatible
    end_d = pd.Timestamp(days[-1]).date()  # type: ignore[arg-type]  # DatetimeIndex item; runtime is Timestamp-compatible
    poll_day_idx_list: list[int] = []
    for md in mid_dates:
        md_ts = pd.Timestamp(cast(object, md))  # type: ignore[arg-type]  # cast(object) used to suppress prior warning; pd.Timestamp accepts date-like at runtime
        if pd.isna(md_ts):
            raise ValueError("invalid publication midpoint date in tracking")
        md_clean = md_ts.date()
        md2 = max(min(md_clean, end_d), start_d)
        poll_day_idx_list.append(day_to_i[md2])
    poll_day_idx = np.array(poll_day_idx_list, dtype=np.int64)
    return days, poll_day_idx


def observation_sigma(phi: np.ndarray | float) -> np.ndarray | float:
    """Survey observation noise (pp) from the transparency index ``phi``.

    Single source of truth for the heteroskedastic likelihood scale — used by
    the model fit and by walk-forward posterior-predictive scoring.
    """
    return np.clip(6.0 / np.sqrt(np.maximum(phi, 0.05)), 1.0, 25.0)


def fit_tracking_hierarchical(
    tracking: pd.DataFrame,
    *,
    outcome_event_date: date,
    calibration_series: str,
    sample_ppc: bool = False,
    m_star_pp: float | None = None,
    anchor_sigma_pp: float = 0.5,
) -> az.InferenceData:
    """Fit the latent-margin random walk with pollster house effects.

    Args:
        tracking: Cleaned tracking polls (``clean_raw_polls`` output).
        outcome_event_date: Outcome event date; the day grid ends on its eve.
        calibration_series: ``"A"`` or ``"B"`` — selects the m★ convention and
            is recorded in provenance attrs.
        sample_ppc: Extend the InferenceData with posterior predictive draws.
        m_star_pp: Verified outcome margin for the active series. When given,
            a soft Gaussian **outcome anchor** enters the likelihood on the
            terminal latent state: ``m★ ~ Normal(mu_margin[-1], anchor_sigma)``.
            This is what makes the reconstruction's "calibrated forecasting"
            structurally true rather than narrative. Leave ``None`` for honest
            out-of-sample validation (walk-forward must never see the outcome).
        anchor_sigma_pp: Anchor strength in percentage points. Small values
            pin the terminal margin to m★; large values let poll evidence
            dominate. Sensitivity is exercised in
            ``tests/test_outcome_anchor.py``.
    """
    if tracking.empty:
        raise ValueError("tracking dataframe is empty")
    if anchor_sigma_pp <= 0:
        raise ValueError("anchor_sigma_pp must be positive")
    days, poll_day_idx = _build_day_index(tracking, outcome_event_date)
    y = tracking["m_poll_pp"].to_numpy(dtype=np.float64)
    pollsters = sorted(tracking["pollster_id"].astype(str).unique())
    p2i = {p: i for i, p in enumerate(pollsters)}
    pollster_idx = np.array([p2i[str(x)] for x in tracking["pollster_id"]], dtype=np.int64)
    phi = tracking["phi_transparency"].to_numpy(dtype=np.float64)
    sigma_obs = observation_sigma(phi)

    day_labels = [d.strftime("%Y-%m-%d") for d in days]

    coords = {"day": day_labels, "pollster": pollsters}
    with pm.Model(coords=coords) as model:
        sigma_rw = pm.HalfNormal("sigma_rw", 1.5)
        mu_margin = pm.GaussianRandomWalk("mu_margin", sigma=sigma_rw, dims="day")
        sigma_h = pm.HalfNormal("sigma_house", 2.5)
        house_offset = pm.Normal("house_offset", 0.0, sigma=sigma_h, dims="pollster")
        mu_poll = mu_margin[poll_day_idx] + house_offset[pollster_idx]
        pm.Normal("obs", mu=mu_poll, sigma=sigma_obs, observed=y)
        if m_star_pp is not None:
            # Soft terminal anchor: the verified outcome margin constrains the
            # latent margin on the eve of the outcome event. House effects do
            # NOT enter — the outcome is not a survey measurement.
            pm.Normal(
                "outcome_anchor",
                mu=mu_margin[-1],
                sigma=float(anchor_sigma_pp),
                observed=float(m_star_pp),
            )
        sk = _sampler_kwargs()
        idata = pm.sample(**sk, progressbar=False)
        if sample_ppc:
            pm.sample_posterior_predictive(
                idata, model=model, extend_inferencedata=True, progressbar=False
            )
    idata.attrs["calibration_series"] = calibration_series
    idata.attrs["model_version"] = MODEL_VERSION
    idata.attrs["interval_type"] = INTERVAL_TYPE
    idata.attrs["interval_prob"] = float(HDI_PROB)
    idata.attrs["outcome_anchor_m_star_pp"] = "" if m_star_pp is None else float(m_star_pp)
    idata.attrs["outcome_anchor_sigma_pp"] = float(anchor_sigma_pp)
    return idata


def _hdi_low_high(post: Any, hdi_prob: float = HDI_PROB) -> tuple[np.ndarray, np.ndarray]:
    """Return (low, high) bounds of a true highest-density interval.

    ``post`` is a posterior DataArray carrying ``chain``/``draw`` sample dims plus
    one parameter dim. We use ``az.hdi`` (minimum-width interval) so the stored
    ``*_hdi_*`` columns and the "94% HDI" figure titles are honest. The previous
    implementation stored 5th/95th equal-tailed quantiles — a 90% interval — under
    HDI names, which is what AUD interval-mislabel flagged.
    """
    hdi = az.hdi(post, hdi_prob=hdi_prob)
    if hasattr(hdi, "data_vars"):  # Dataset → take its single data variable
        hdi = hdi[next(iter(hdi.data_vars))]
    low = np.asarray(hdi.sel(hdi="lower").values, dtype=float).reshape(-1)
    high = np.asarray(hdi.sel(hdi="higher").values, dtype=float).reshape(-1)
    return low, high


def export_daily_posterior_table(
    idata: az.InferenceData,
    days: pd.DatetimeIndex,
    calibration_series: str,
) -> pd.DataFrame:
    post = idata.posterior["mu_margin"]  # type: ignore[union-attr]  # arviz stubs omit InferenceData.posterior; runtime is xarray.Dataset
    mean_m = np.asarray(post.mean(dim=("chain", "draw")).values).reshape(-1)
    low, high = _hdi_low_high(post)
    rows = []
    for i, d in enumerate(days):
        rows.append(
            {
                "date": d.date(),
                "calibration_series": calibration_series,
                "series_tag": calibration_series,
                "posterior_mean_preference_margin_pp": float(mean_m[i]),
                "posterior_hdi_low_pp": float(low[i]),
                "posterior_hdi_high_pp": float(high[i]),
                "model_version": MODEL_VERSION,
            }
        )
    return pd.DataFrame(rows)


def export_house_effects_table(
    idata: az.InferenceData,
    pollsters: list[str],
    calibration_series: str,
    tracking: pd.DataFrame,
) -> pd.DataFrame:
    post = idata.posterior["house_offset"]  # type: ignore[union-attr]  # arviz stubs omit InferenceData.posterior; runtime is xarray.Dataset
    mean_m = np.asarray(post.mean(dim=("chain", "draw")).values).reshape(-1)
    low, high = _hdi_low_high(post)
    fam = tracking.groupby("pollster_id")["pollster_bias_family"].first()
    rows = []
    for i, p in enumerate(pollsters):
        rows.append(
            {
                "pollster_id": p,
                "calibration_series": calibration_series,
                "house_effect_posterior_mean": float(mean_m[i]),
                "house_effect_hdi_low": float(low[i]),
                "house_effect_hdi_high": float(high[i]),
                "pollster_bias_family": str(fam.get(p, "default")),
                "model_version": MODEL_VERSION,
            }
        )
    return pd.DataFrame(rows)


def run_tracking_fit_and_export(
    tracking: pd.DataFrame,
    out_dir: Path,
    *,
    outcome_event_date: date,
    calibration_series: str,
    m_star_pp: float | None = None,
    anchor_sigma_pp: float = 0.5,
) -> tuple[az.InferenceData, pd.DataFrame, pd.DataFrame]:
    days, _ = _build_day_index(tracking, outcome_event_date)
    idata = fit_tracking_hierarchical(
        tracking,
        outcome_event_date=outcome_event_date,
        calibration_series=calibration_series,
        m_star_pp=m_star_pp,
        anchor_sigma_pp=anchor_sigma_pp,
    )
    pollsters = sorted(tracking["pollster_id"].astype(str).unique())
    daily = export_daily_posterior_table(idata, days, calibration_series)
    houses = export_house_effects_table(idata, pollsters, calibration_series, tracking)
    out_dir.mkdir(parents=True, exist_ok=True)
    daily.to_parquet(out_dir / "daily_posterior_forecast.parquet", index=False)
    houses.to_parquet(out_dir / "posterior_house_effects.parquet", index=False)
    return idata, daily, houses

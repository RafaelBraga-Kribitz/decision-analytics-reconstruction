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

MODEL_VERSION = "c_tracking_hierarchical_v0.1"


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
    return {
        "chains": int(cfg.get("chains", 2)),
        "draws": int(cfg.get("draws", 400)),
        "tune": int(cfg.get("tune", 400)),
        "target_accept": float(cfg.get("target_accept", 0.9)),
        "random_seed": int(cfg.get("random_seed", 42)),
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
        d_i = pd.Timestamp(days.iloc[i]).date()
        day_to_i[d_i] = i
    start_d = pd.Timestamp(days.iloc[0]).date()
    end_d = pd.Timestamp(days.iloc[-1]).date()
    poll_day_idx_list: list[int] = []
    for md in mid_dates:
        md_ts = pd.Timestamp(cast(object, md))
        if pd.isna(md_ts):
            raise ValueError("invalid publication midpoint date in tracking")
        md_clean = md_ts.date()
        md2 = max(min(md_clean, end_d), start_d)
        poll_day_idx_list.append(day_to_i[md2])
    poll_day_idx = np.array(poll_day_idx_list, dtype=np.int64)
    return days, poll_day_idx


def fit_tracking_hierarchical(
    tracking: pd.DataFrame,
    *,
    outcome_event_date: date,
    calibration_series: str,
) -> az.InferenceData:
    if tracking.empty:
        raise ValueError("tracking dataframe is empty")
    days, poll_day_idx = _build_day_index(tracking, outcome_event_date)
    y = tracking["m_poll_pp"].to_numpy(dtype=np.float64)
    pollsters = sorted(tracking["pollster_id"].astype(str).unique())
    p2i = {p: i for i, p in enumerate(pollsters)}
    pollster_idx = np.array([p2i[str(x)] for x in tracking["pollster_id"]], dtype=np.int64)
    phi = tracking["phi_transparency"].to_numpy(dtype=np.float64)
    sigma_obs = np.clip(6.0 / np.sqrt(np.maximum(phi, 0.05)), 1.0, 25.0)

    day_labels = [d.strftime("%Y-%m-%d") for d in days]

    coords = {"day": day_labels, "pollster": pollsters}
    with pm.Model(coords=coords):
        sigma_rw = pm.HalfNormal("sigma_rw", 1.5)
        mu_margin = pm.GaussianRandomWalk("mu_margin", sigma=sigma_rw, dims="day")
        sigma_h = pm.HalfNormal("sigma_house", 2.5)
        house_offset = pm.Normal("house_offset", 0.0, sigma=sigma_h, dims="pollster")
        mu_poll = mu_margin[poll_day_idx] + house_offset[pollster_idx]
        pm.Normal("obs", mu=mu_poll, sigma=sigma_obs, observed=y)
        sk = _sampler_kwargs()
        idata = pm.sample(**sk, progressbar=False)
    idata.attrs["calibration_series"] = calibration_series
    idata.attrs["model_version"] = MODEL_VERSION
    return idata


def export_daily_posterior_table(
    idata: az.InferenceData,
    days: pd.DatetimeIndex,
    calibration_series: str,
) -> pd.DataFrame:
    post = idata.posterior["mu_margin"]  # type: ignore[union-attr]
    mean_m = post.mean(dim=("chain", "draw")).values
    low = post.quantile(0.05, dim=("chain", "draw")).values
    high = post.quantile(0.95, dim=("chain", "draw")).values
    mean_m = np.asarray(mean_m).reshape(-1)
    low = np.asarray(low).reshape(-1)
    high = np.asarray(high).reshape(-1)
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
    post = idata.posterior["house_offset"]  # type: ignore[union-attr]
    mean_m = post.mean(dim=("chain", "draw")).values.flatten()
    low = post.quantile(0.05, dim=("chain", "draw")).values.flatten()
    high = post.quantile(0.95, dim=("chain", "draw")).values.flatten()
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
) -> tuple[az.InferenceData, pd.DataFrame, pd.DataFrame]:
    days, _ = _build_day_index(tracking, outcome_event_date)
    idata = fit_tracking_hierarchical(
        tracking,
        outcome_event_date=outcome_event_date,
        calibration_series=calibration_series,
    )
    pollsters = sorted(tracking["pollster_id"].astype(str).unique())
    daily = export_daily_posterior_table(idata, days, calibration_series)
    houses = export_house_effects_table(idata, pollsters, calibration_series, tracking)
    out_dir.mkdir(parents=True, exist_ok=True)
    daily.to_parquet(out_dir / "daily_posterior_forecast.parquet", index=False)
    houses.to_parquet(out_dir / "posterior_house_effects.parquet", index=False)
    return idata, daily, houses

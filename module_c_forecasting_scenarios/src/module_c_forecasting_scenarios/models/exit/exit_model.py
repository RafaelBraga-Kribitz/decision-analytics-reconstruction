"""Exit / quick-count bias layer — separate from tracking likelihood."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pymc as pm
import yaml

from module_c_forecasting_scenarios.paths import module_config_dir

MODEL_VERSION = "c_exit_bias_v0.1"


def _exit_sampler_kwargs() -> dict:
    path = module_config_dir() / "pymc_sampler.yaml"
    with open(path) as f:
        cfg = yaml.safe_load(f)
    if os.environ.get("MC_FAST"):
        return {
            "chains": 2,
            "draws": int(cfg["draws_fast"]),
            "tune": int(cfg["tune_fast"]),
            "target_accept": 0.90,
            "random_seed": int(cfg.get("random_seed", 42)),
        }
    return {
        "chains": int(cfg.get("chains", 4)),
        "draws": int(cfg.get("draws", 1000)),
        "tune": int(cfg.get("tune", 1000)),
        "target_accept": float(cfg.get("target_accept", 0.95)),
        "random_seed": int(cfg.get("random_seed", 42)),
        "nuts_sampler_kwargs": {"max_treedepth": int(cfg.get("max_treedepth", 10))},
    }


def fit_exit_quickcount(
    exit_df: pd.DataFrame, *, calibration_series: str
) -> tuple[pd.DataFrame, object | None]:
    """Bayesian normal model for exit margin with OEA/EU timing flags as linear covariates."""
    if exit_df.shape[0] < 2:
        summary = pd.DataFrame(
            [
                {
                    "calibration_series": calibration_series,
                    "model_version": MODEL_VERSION,
                    "note": "insufficient_exit_rows_for_regression",
                    "m_poll_pp_mean": (
                        float(exit_df["m_poll_pp"].mean()) if len(exit_df) else float("nan")
                    ),
                }
            ]
        )
        return summary, None
    y = exit_df["m_poll_pp"].to_numpy(dtype=np.float64)
    oea = exit_df["oea_timing_compliant"].fillna(False).astype(float).to_numpy()
    eu = exit_df["eu_release_window_flag"].fillna(False).astype(float).to_numpy()
    with pm.Model():
        intercept = pm.Normal("intercept", mu=60.0, sigma=15.0)
        beta_oea = pm.Normal("beta_oea", mu=0.0, sigma=5.0)
        beta_eu = pm.Normal("beta_eu", mu=0.0, sigma=5.0)
        sigma = pm.HalfNormal("sigma", 8.0)
        mu = intercept + beta_oea * oea + beta_eu * eu
        pm.Normal("obs", mu=mu, sigma=sigma, observed=y)
        idata = pm.sample(**_exit_sampler_kwargs(), progressbar=False)
    post = idata.posterior  # type: ignore[union-attr]  # arviz stubs omit InferenceData.posterior; runtime is xarray.Dataset
    rows = []
    for v in ("intercept", "beta_oea", "beta_eu", "sigma"):
        s = post[v].stack(sample=("chain", "draw"))
        rows.append(
            {
                "parameter": v,
                "posterior_mean": float(s.mean().values),
                "hdi_low": float(s.quantile(0.05).values),
                "hdi_high": float(s.quantile(0.95).values),
                "calibration_series": calibration_series,
                "model_version": MODEL_VERSION,
            }
        )
    return pd.DataFrame(rows), idata

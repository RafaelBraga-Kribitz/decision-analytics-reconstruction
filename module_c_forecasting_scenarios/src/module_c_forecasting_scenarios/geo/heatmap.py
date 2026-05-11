"""Department-level battleground win probabilities (synthetic mapping from national margin)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

from module_b_resource_allocation.constants import DEPARTMENTS

MODEL_VERSION = "c_battleground_v0.1"


def export_battleground_department_table(
    daily_forecast: pd.DataFrame,
    out_path: Path,
    *,
    calibration_series: str,
    seed: int = 42,
) -> pd.DataFrame:
    """Map last-day posterior margin to per-department win probability with deterministic jitter."""
    df = daily_forecast.sort_values("date")
    last = float(df.iloc[-1]["posterior_mean_preference_margin_pp"])
    rng = np.random.default_rng(seed)
    rows = []
    for i, d in enumerate(DEPARTMENTS):
        noise = (rng.random() - 0.5) * 0.08
        z = 0.12 * (last - 3.8) + noise + 0.001 * i
        p = float(expit(z))
        rows.append(
            {
                "department": d,
                "calibration_series": calibration_series,
                "win_probability_a": p,
                "model_version": MODEL_VERSION,
            }
        )
    out = pd.DataFrame(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_path, index=False)
    geo = {"type": "FeatureCollection", "features": []}
    for _, r in out.iterrows():
        geo["features"].append(
            {
                "type": "Feature",
                "properties": {
                    "department": r["department"],
                    "win_probability_a": r["win_probability_a"],
                    "calibration_series": calibration_series,
                },
                "geometry": None,
            }
        )
    out_path.with_suffix(".geojson").write_text(json.dumps(geo))
    return out

"""Department-level battleground win probabilities (synthetic mapping from national margin)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from module_b_resource_allocation.constants import DEPARTMENTS
from scipy.special import expit

MODEL_VERSION = "c_battleground_v0.1"

_DEPT_POLYGONS_PATH = Path(__file__).parent / "paraguay_departments.geojson"


def _load_department_polygons() -> dict[str, Any]:
    """Return mapping department_name → GeoJSON geometry dict."""
    geo = json.loads(_DEPT_POLYGONS_PATH.read_text())
    return {f["properties"]["department"]: f["geometry"] for f in geo["features"]}


def export_battleground_department_table(
    daily_forecast: pd.DataFrame,
    out_path: Path,
    *,
    calibration_series: str,
    seed: int = 42,
) -> pd.DataFrame:
    """Map last-day posterior margin to per-department win probability with deterministic jitter.

    Writes three outputs alongside out_path:
    - ``{stem}.parquet`` — contract-validated 4-column table
    - ``{stem}.geojson`` — null-geometry GeoJSON (backward compat)
    - ``battleground_probability_heatmap.geojson`` — polygon-geometry choropleth GeoJSON
    """
    df = daily_forecast.sort_values("date")
    last_row = df.iloc[-1]
    last = float(last_row["posterior_mean_preference_margin_pp"])
    last_lo = float(last_row.get("posterior_hdi_low_pp", last - 2.0))  # type: ignore[arg-type]
    last_hi = float(last_row.get("posterior_hdi_high_pp", last + 2.0))  # type: ignore[arg-type]

    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for i, d in enumerate(DEPARTMENTS):
        noise = (rng.random() - 0.5) * 0.08
        z = 0.12 * (last - 3.8) + noise + 0.001 * i
        z_lo = 0.12 * (last_lo - 3.8) + noise + 0.001 * i
        z_hi = 0.12 * (last_hi - 3.8) + noise + 0.001 * i
        rows.append(
            {
                "department": d,
                "calibration_series": calibration_series,
                "win_probability_a": float(expit(z)),
                "model_version": MODEL_VERSION,
                "_posterior_win_prob": float(expit(z)),
                "_hdi_low": float(expit(z_lo)),
                "_hdi_high": float(expit(z_hi)),
            }
        )

    full = pd.DataFrame(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Parquet: contract fields only.
    contract_cols = ["department", "calibration_series", "win_probability_a", "model_version"]
    out = full[contract_cols].copy()
    out.to_parquet(out_path, index=False)

    # Null-geometry GeoJSON (backward compat).
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

    # Polygon-geometry choropleth GeoJSON.
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

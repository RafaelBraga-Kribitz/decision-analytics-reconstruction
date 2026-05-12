"""Monte Carlo scenario engine (10k runs) + shock catalog YAML."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml

from module_c_forecasting_scenarios.paths import module_config_dir, repo_root


def _mc_n() -> int:
    if os.environ.get("MC_FAST"):
        return 200
    return 10_000


def run_monte_carlo_scenarios(
    tracking: pd.DataFrame,
    allocation_path: Path | None,
    *,
    out_dir: Path,
    shock_multiplier: float | None = None,
    baseline_shock_zero: bool = False,
) -> dict[str, Any]:
    """Stratified draws using shock_score_s and scenario_bucket from tracking."""
    out_dir.mkdir(parents=True, exist_ok=True)
    n = _mc_n()
    rng = np.random.default_rng(42)
    p = yaml.safe_load((module_config_dir() / "shock_params.yaml").read_text())
    mult = float(
        shock_multiplier if shock_multiplier is not None else p.get("shock_multiplier", 1.0)
    )
    baseline_zero = baseline_shock_zero or bool(p.get("baseline_shock_zero", False))

    shocks: list[dict[str, Any]] = []
    if "shock_score_s" not in tracking.columns:
        raise ValueError("tracking must include shock_score_s (run cleaning attach_shock_scores)")
    for _i, row in tracking.iterrows():
        sid = f"shock_{row['poll_wave_id']}"
        pub_ts = pd.Timestamp(cast(object, row.at["publication_date"]))
        if pd.isna(pub_ts):
            raise ValueError("invalid publication_date in tracking row")
        pub = pub_ts.date()
        ts = datetime.combine(pub, datetime.min.time(), tzinfo=UTC).isoformat()
        score = float(row["shock_score_s"]) * mult
        if baseline_zero:
            score = 0.0
        shocks.append(
            {
                "shock_id": sid,
                "poll_wave_id": row["poll_wave_id"],
                "shock_score_s": score,
                "scenario_bucket": str(row["scenario_bucket"]),
                "shock_timestamp_utc": ts,
            }
        )
    cat_path = out_dir / "monte_carlo_shock_catalog.yaml"
    with open(cat_path, "w") as f:
        yaml.safe_dump({"shocks": shocks}, f, sort_keys=False)

    alloc_mean_contacts = 0.0
    if allocation_path and allocation_path.exists():
        adf = pd.read_parquet(allocation_path)
        handshake_cols = ("persuasion_adjusted_contacts", "expected_contacts", "scenario_id")
        for c in handshake_cols:
            if c not in adf.columns:
                raise ValueError(f"allocation_output missing handshake column {c!r}")
        alloc_mean_contacts = float(adf["persuasion_adjusted_contacts"].mean())

    draws = []
    buckets = tracking["scenario_bucket"].to_numpy()
    scores = tracking["shock_score_s"].to_numpy(dtype=np.float64) * mult
    if baseline_zero:
        scores = np.zeros_like(scores, dtype=np.float64)
    w = np.maximum(scores, 1e-6)
    w = w / w.sum()
    for k in range(n):
        j = int(rng.choice(len(tracking), p=w))
        draws.append(
            {
                "draw_id": k,
                "poll_wave_id": str(tracking.iloc[j]["poll_wave_id"]),
                "scenario_bucket": str(buckets[j]),
                "shock_scale": float(scores[j]),
                "alloc_mean_persuasion_contacts": alloc_mean_contacts,
            }
        )
    draws_df = pd.DataFrame(draws)
    draws_df.to_parquet(out_dir / "monte_carlo_draws.parquet", index=False)

    manifest = {
        "n_draws": n,
        "seed": 42,
        "shock_multiplier": mult,
        "baseline_shock_zero": baseline_zero,
        "allocation_input": str(allocation_path) if allocation_path else None,
        "repo_root": str(repo_root()),
        "created_at_utc": datetime.now(tz=UTC).isoformat(),
    }
    (out_dir / "scenario_run_manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest

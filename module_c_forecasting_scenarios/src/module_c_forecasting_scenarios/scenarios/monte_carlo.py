"""Monte Carlo scenario engine — stratified across the three canonical buckets.

Default size is 10 000 draws (``MC_FAST=1`` shrinks to 600 for CI smoke).
Draws are split evenly across the canonical scenario buckets
(``baseline``, ``extreme_tracker``, ``compounded_herd``); for any bucket
absent from the tracking fixture, draws are synthesised from a LogNormal
prior in ``shock_params.yaml:bucket_priors`` so the resulting parquet
always covers the full canonical space (required by
``schema_contracts/monte_carlo_draws.yaml``).
"""

from __future__ import annotations

import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd
import yaml

from module_c_forecasting_scenarios.paths import module_config_dir, repo_root

CANONICAL_BUCKETS: Final[tuple[str, str, str]] = (
    "baseline",
    "extreme_tracker",
    "compounded_herd",
)


def _mc_n() -> int:
    if os.environ.get("MC_FAST"):
        return 600
    return 10_000


def _bucket_share(n: int, k: int) -> list[int]:
    """Split ``n`` into ``k`` near-equal parts (first parts absorb remainder)."""
    base = n // k
    rem = n - base * k
    return [base + (1 if i < rem else 0) for i in range(k)]


def _scenario_adjusted_contacts(alloc_mean_contacts: float, shock_scale: float) -> float:
    """Per-draw effective persuasion contacts = baseline mean × engagement shock.

    The B→C handshake passes a single scenario-invariant mean
    (``alloc_mean_persuasion_contacts``); the scenario severity lives entirely in
    ``shock_scale``. This is the *effective* contact volume each draw's shock
    implies — the propagation the monte_carlo_draws contract always described
    ("shock_scale ... propagated to allocation outcomes") but the engine never
    actually applied, which is why the published "persuasion-adjusted contacts"
    figure was a flat line. It varies by draw and by bucket. This is a
    scenario-adjusted (effective) quantity, not raw allocated contacts.
    """
    return float(alloc_mean_contacts) * float(shock_scale)


def _draw_from_tracking(
    bucket_rows: pd.DataFrame,
    n: int,
    mult: float,
    rng: np.random.Generator,
    alloc_mean_contacts: float,
    start_idx: int,
) -> list[dict[str, object]]:
    scores = bucket_rows["shock_score_s"].to_numpy(dtype=np.float64) * mult
    w = np.maximum(scores, 1e-6)
    w = w / w.sum()
    draws: list[dict[str, object]] = []
    for k in range(n):
        j = int(rng.choice(len(bucket_rows), p=w))
        draws.append(
            {
                "draw_id": start_idx + k,
                "poll_wave_id": str(bucket_rows.iloc[j]["poll_wave_id"]),
                "scenario_bucket": str(bucket_rows.iloc[j]["scenario_bucket"]),
                "shock_scale": float(scores[j]),
                "alloc_mean_persuasion_contacts": alloc_mean_contacts,
                "scenario_adjusted_persuasion_contacts": _scenario_adjusted_contacts(
                    alloc_mean_contacts, float(scores[j])
                ),
                "draw_source": "tracking_sample",
            }
        )
    return draws


def _draw_from_prior(
    bucket: str,
    n: int,
    prior: dict[str, float],
    mult: float,
    rng: np.random.Generator,
    alloc_mean_contacts: float,
    start_idx: int,
) -> list[dict[str, object]]:
    log_mean = float(prior["log_mean"])
    log_sd = float(prior["log_sd"])
    z = rng.normal(loc=log_mean, scale=log_sd, size=n)
    shocks = np.exp(z) * mult
    return [
        {
            "draw_id": start_idx + i,
            "poll_wave_id": None,
            "scenario_bucket": bucket,
            "shock_scale": float(shocks[i]),
            "alloc_mean_persuasion_contacts": alloc_mean_contacts,
            "scenario_adjusted_persuasion_contacts": _scenario_adjusted_contacts(
                alloc_mean_contacts, float(shocks[i])
            ),
            "draw_source": "synthetic_prior",
        }
        for i in range(n)
    ]


def _write_shock_catalog(
    tracking: pd.DataFrame,
    out_dir: Path,
    mult: float,
    baseline_zero: bool,
) -> None:
    shocks: list[dict[str, object]] = []
    for _i, row in tracking.iterrows():
        sid = f"shock_{row['poll_wave_id']}"
        pub_ts = pd.Timestamp(cast(object, row.at["publication_date"]))  # type: ignore[arg-type]
        if pd.isna(pub_ts):
            raise ValueError("invalid publication_date in tracking row")
        ts = datetime.combine(pub_ts.date(), datetime.min.time(), tzinfo=UTC).isoformat()
        score = float(row["shock_score_s"]) * mult
        if baseline_zero:
            score = 0.0
        shocks.append(
            {
                "shock_id": sid,
                "poll_wave_id": str(row["poll_wave_id"]),
                "shock_score_s": score,
                "scenario_bucket": str(row["scenario_bucket"]),
                "shock_timestamp_utc": ts,
            }
        )
    cat_path = out_dir / "monte_carlo_shock_catalog.yaml"
    with open(cat_path, "w") as f:
        yaml.safe_dump({"shocks": shocks}, f, sort_keys=False)


def _load_allocation_mean_contacts(allocation_path: Path | None) -> float:
    if allocation_path is None:
        return 0.0
    if not allocation_path.exists():
        raise FileNotFoundError(
            f"allocation parquet not found at {allocation_path}; "
            "run the Module B pipeline first (make module-b-allocate)"
        )
    adf = pd.read_parquet(allocation_path)
    handshake_cols = ("persuasion_adjusted_contacts", "expected_contacts", "scenario_id")
    for c in handshake_cols:
        if c not in adf.columns:
            raise ValueError(f"allocation_output missing handshake column {c!r}")
    alloc_mean_contacts = float(adf["persuasion_adjusted_contacts"].mean())
    if alloc_mean_contacts <= 0.0:
        raise ValueError(
            f"allocation parquet {allocation_path} has non-positive mean persuasion "
            "contacts — the B→C handshake would be a silent zero"
        )
    return alloc_mean_contacts


def _stratified_bucket_draws(
    tracking: pd.DataFrame,
    n: int,
    mult: float,
    baseline_zero: bool,
    rng: np.random.Generator,
    alloc_mean_contacts: float,
    bucket_priors: dict[str, object],
) -> list[dict[str, object]]:
    bucket_quota = _bucket_share(n, len(CANONICAL_BUCKETS))
    effective_mult = 0.0 if baseline_zero else mult
    all_draws: list[dict[str, object]] = []
    cursor = 0
    for bucket, quota in zip(CANONICAL_BUCKETS, bucket_quota, strict=True):
        bucket_rows = cast(pd.DataFrame, tracking[tracking["scenario_bucket"] == bucket])
        if len(bucket_rows) > 0:
            chunk = _draw_from_tracking(
                bucket_rows,
                n=quota,
                mult=effective_mult,
                rng=rng,
                alloc_mean_contacts=alloc_mean_contacts,
                start_idx=cursor,
            )
        else:
            prior = bucket_priors.get(bucket)
            if prior is None:
                raise ValueError(
                    f"bucket {bucket!r} missing from tracking AND from shock_params bucket_priors"
                )
            chunk = _draw_from_prior(
                bucket=bucket,
                n=quota,
                prior=cast(dict[str, float], prior),
                mult=effective_mult,
                rng=rng,
                alloc_mean_contacts=alloc_mean_contacts,
                start_idx=cursor,
            )
        all_draws.extend(chunk)
        cursor += quota
    return all_draws


def run_monte_carlo_scenarios(
    tracking: pd.DataFrame,
    allocation_path: Path | None,
    *,
    out_dir: Path,
    shock_multiplier: float | None = None,
    baseline_shock_zero: bool = False,
    n_draws: int | None = None,
) -> dict[str, object]:
    """Stratified MC draws across all canonical buckets."""
    out_dir.mkdir(parents=True, exist_ok=True)
    n = int(n_draws) if n_draws is not None else _mc_n()
    rng = np.random.default_rng(42)
    p = yaml.safe_load((module_config_dir() / "shock_params.yaml").read_text())
    mult = float(
        shock_multiplier if shock_multiplier is not None else p.get("shock_multiplier", 1.0)
    )
    baseline_zero = baseline_shock_zero or bool(p.get("baseline_shock_zero", False))
    bucket_priors = p.get("bucket_priors", {})

    if "shock_score_s" not in tracking.columns:
        raise ValueError("tracking must include shock_score_s (run cleaning attach_shock_scores)")

    _write_shock_catalog(tracking, out_dir, mult, baseline_zero)
    alloc_mean_contacts = _load_allocation_mean_contacts(allocation_path)
    all_draws = _stratified_bucket_draws(
        tracking,
        n,
        mult,
        baseline_zero,
        rng,
        alloc_mean_contacts,
        bucket_priors,
    )

    draws_df = pd.DataFrame(all_draws)
    draws_df.to_parquet(out_dir / "monte_carlo_draws.parquet", index=False)

    bucket_quota = _bucket_share(n, len(CANONICAL_BUCKETS))
    manifest = {
        "n_draws": n,
        "seed": 42,
        "shock_multiplier": mult,
        "baseline_shock_zero": baseline_zero,
        "allocation_input": str(allocation_path) if allocation_path else None,
        "canonical_buckets": list(CANONICAL_BUCKETS),
        "bucket_quotas": dict(zip(CANONICAL_BUCKETS, bucket_quota, strict=True)),
        "buckets_synthesised_from_prior": [
            b for b in CANONICAL_BUCKETS if len(tracking[tracking["scenario_bucket"] == b]) == 0
        ],
        "repo_root": str(repo_root()),
        "created_at_utc": datetime.now(tz=UTC).isoformat(),
    }
    (out_dir / "scenario_run_manifest.json").write_text(json.dumps(manifest, indent=2))
    # Math sanity: each bucket quota sums to n.
    assert sum(bucket_quota) == n
    assert math.isclose(sum(bucket_quota), n)
    return cast(dict[str, object], manifest)

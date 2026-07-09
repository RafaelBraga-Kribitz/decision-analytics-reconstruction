"""Monte Carlo scenario engine — stratified across the three canonical buckets.

Default size is 10 000 draws (``MC_FAST=1`` shrinks to 600 for CI smoke).
Draws are split evenly (equal-allocation stratification) across the
canonical scenario buckets (``baseline``, ``extreme_tracker``,
``compounded_herd``); for any bucket absent from the tracking fixture, draws
are synthesised from a LogNormal prior in ``shock_params.yaml:bucket_priors``
so the resulting parquet always covers the full canonical space (required by
``schema_contracts/monte_carlo_draws.yaml``).

**Reweighting (IMP-C08 / audit C14):** equal-thirds allocation is a
variance-reduction *design*, not a claim that the three buckets are equally
likely. Every draw carries a ``draw_weight`` column —
``prevalence(bucket) / design_share(bucket)`` — where ``prevalence`` is the
empirical fraction of *observed* tracking polls assigned to that bucket
(recomputed fresh from the ``tracking`` argument on every call — never
cached, so it cannot silently drift from the data it describes) and
``design_share`` is that bucket's equal-thirds sampling fraction (~1/3). Any
statistic pooled across buckets (mean, quantile) MUST use ``draw_weight`` —
see :func:`weighted_pooled_mean`, :func:`weighted_pooled_quantile`, and
:func:`effective_sample_size`. Per-bucket (conditional-on-scenario) views may
ignore the weight; it exists only to correct pooling across buckets.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd
import yaml

from module_c_forecasting_scenarios.data.contract_validate import validate_dataframe_contract
from module_c_forecasting_scenarios.paths import module_config_dir, repo_root

CANONICAL_BUCKETS: Final[tuple[str, str, str]] = (
    "baseline",
    "extreme_tracker",
    "compounded_herd",
)


def _mc_n() -> int:
    """Monte Carlo draw budget, derived from a stated MC-standard-error target.

    [PARAM] no prior derivation existed -> target_mc_se_pp=0.1, assumed_sigma_pp=10.0 (new,
    documented here; the resulting n values, 10_000 / 600, are unchanged).

    MC-SE of a pooled mean is ``sigma / sqrt(n)``. Conservatively bounding the
    headline pooled statistic's per-draw dispersion at ``sigma <= 10`` pp
    (order of magnitude of the extreme-bucket margin cutoff,
    ``shock_params.yaml:m_star_extreme_pp``) and targeting MC-SE <= 0.1 pp for
    full report-grade runs:

        n = (sigma / target_mc_se)^2 = (10 / 0.1)^2 = 10_000

    ``MC_FAST=1`` (600 draws, 200 per bucket at equal thirds) is an
    engineering budget for CI runtime, not an MC-SE-derived value — it is
    never used for report-grade statistics, only for schema/contract/mapping
    tests that need bucket coverage, not precision (MC-SE at n=600 is
    ``10/sqrt(600) ~= 0.41`` pp).

    Returns:
        The draw budget: 600 under ``MC_FAST=1``, else 10 000.

    Raises:
        None.

    Example:
        >>> import os
        >>> os.environ["MC_FAST"] = "1"
        >>> _mc_n()
        600
    """
    if os.environ.get("MC_FAST"):
        return 600
    return 10_000


def _bucket_share(n: int, k: int) -> list[int]:
    """Split ``n`` into ``k`` near-equal parts (first parts absorb remainder)."""
    base = n // k
    rem = n - base * k
    return [base + (1 if i < rem else 0) for i in range(k)]


def empirical_bucket_prevalence(
    tracking: pd.DataFrame, buckets: tuple[str, ...] = CANONICAL_BUCKETS
) -> dict[str, float]:
    """Empirical scenario-bucket prevalence among observed tracking polls.

    Computed fresh from ``tracking["scenario_bucket"]`` on every call (never
    cached), so it cannot silently drift from the data used to derive it
    (IMP-C08 negative constraint: "preventing silent prevalence drift").

    Args:
        tracking: Cleaned tracking-wave rows with a ``scenario_bucket``
            column (``features.shock_scores.scenario_bucket_for_margin``
            output already attached by the cleaning pipeline).
        buckets: The canonical bucket names to report prevalence for. Buckets
            absent from ``tracking`` get prevalence 0.0 (the "empty bucket"
            edge case).

    Returns:
        Mapping of bucket name -> fraction of tracking rows in that bucket.
        Sums to 1.0 when ``tracking`` is non-empty and every row's bucket is
        one of ``buckets``; empty ``tracking`` returns 0.0 for every bucket.

    Raises:
        KeyError: If ``tracking`` lacks a ``scenario_bucket`` column and is
            non-empty.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"scenario_bucket": ["baseline", "baseline", "extreme_tracker"]})
        >>> empirical_bucket_prevalence(df)["baseline"]
        0.6666666666666666
    """
    total = len(tracking)
    if total == 0:
        return {b: 0.0 for b in buckets}
    counts = tracking["scenario_bucket"].value_counts()
    return {b: float(counts.get(b, 0)) / total for b in buckets}  # type: ignore[arg-type]  # Series.get default; runtime is int|float


def _design_shares(n: int, buckets: tuple[str, ...] = CANONICAL_BUCKETS) -> dict[str, float]:
    """Equal-allocation sampling fraction per bucket (``quota / n``)."""
    quotas = _bucket_share(n, len(buckets))
    return {b: (q / n if n > 0 else 0.0) for b, q in zip(buckets, quotas, strict=True)}


def _draw_weight_for_bucket(
    bucket: str, prevalence: dict[str, float], design_share: dict[str, float]
) -> float:
    """Importance weight ``prevalence(bucket) / design_share(bucket)``, safe at 0."""
    share = design_share.get(bucket, 0.0)
    if share <= 0.0:
        return 0.0
    return prevalence.get(bucket, 0.0) / share


def weighted_pooled_mean(
    draws: pd.DataFrame, value_col: str, weight_col: str = "draw_weight"
) -> float:
    """Weighted pooled mean of ``value_col`` across all buckets.

    Args:
        draws: Monte Carlo draws with ``value_col`` and ``weight_col``
            columns (e.g. the ``monte_carlo_draws.parquet`` output).
        value_col: Column to average.
        weight_col: Column of per-draw importance weights (default
            ``"draw_weight"``).

    Returns:
        ``sum(weight * value) / sum(weight)``.

    Raises:
        ValueError: If ``weight_col`` sums to <= 0 (no informative weights to
            pool with).

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"x": [1.0, 3.0], "draw_weight": [1.0, 1.0]})
        >>> weighted_pooled_mean(df, "x")
        2.0
    """
    w = draws[weight_col].to_numpy(dtype=np.float64)
    x = draws[value_col].to_numpy(dtype=np.float64)
    total_w = float(w.sum())
    if total_w <= 0.0:
        raise ValueError(f"{weight_col!r} sums to <= 0; cannot compute a weighted pooled mean")
    return float(np.sum(w * x) / total_w)


def weighted_pooled_quantile(
    draws: pd.DataFrame, value_col: str, q: float, weight_col: str = "draw_weight"
) -> float:
    """Weighted pooled quantile of ``value_col`` across all buckets.

    Uses the standard weighted-quantile construction: sort by value, form the
    weight-normalized cumulative distribution at each value's midpoint, and
    linearly interpolate at ``q``.

    Args:
        draws: Monte Carlo draws with ``value_col`` and ``weight_col``
            columns.
        value_col: Column to compute the quantile of.
        q: Quantile in [0, 1].
        weight_col: Column of per-draw importance weights (default
            ``"draw_weight"``).

    Returns:
        The weighted ``q``-quantile of ``value_col``.

    Raises:
        ValueError: If ``weight_col`` sums to <= 0, or ``q`` is outside
            [0, 1].

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"x": [1.0, 2.0, 3.0], "draw_weight": [1.0, 1.0, 1.0]})
        >>> weighted_pooled_quantile(df, "x", 0.5)
        2.0
    """
    if not (0.0 <= q <= 1.0):
        raise ValueError(f"q must be in [0, 1], got {q}")
    w = draws[weight_col].to_numpy(dtype=np.float64)
    x = draws[value_col].to_numpy(dtype=np.float64)
    total_w = float(w.sum())
    if total_w <= 0.0:
        raise ValueError(f"{weight_col!r} sums to <= 0; cannot compute a weighted quantile")
    order = np.argsort(x)
    x_sorted = x[order]
    w_sorted = w[order]
    cum = np.cumsum(w_sorted) - 0.5 * w_sorted
    cum = cum / total_w
    return float(np.interp(q, cum, x_sorted))


def effective_sample_size(draws: pd.DataFrame, weight_col: str = "draw_weight") -> float:
    """Kish effective sample size of the (possibly zero-)weighted draws.

    ``n_eff = (sum w)^2 / sum(w^2)``. This is the standard-error-relevant
    sample size under importance weighting: the MC-SE of a weighted pooled
    mean scales as ``sigma / sqrt(n_eff)``, not ``sigma / sqrt(len(draws))`` —
    the more concentrated the weights, the fewer effective draws a pooled
    statistic actually rests on. See ``METHODOLOGY.md`` § Monte Carlo
    Stratification & Reweighting.

    Args:
        draws: Monte Carlo draws with a ``weight_col`` column.
        weight_col: Column of per-draw importance weights (default
            ``"draw_weight"``).

    Returns:
        The Kish effective sample size. ``0.0`` if every weight is 0.

    Raises:
        None.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"draw_weight": [1.0, 1.0, 1.0, 1.0]})
        >>> effective_sample_size(df)
        4.0
    """
    w = draws[weight_col].to_numpy(dtype=np.float64)
    sw = float(w.sum())
    sw2 = float(np.sum(w * w))
    if sw2 <= 0.0:
        return 0.0
    return (sw * sw) / sw2


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
    draw_weight: float,
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
                "draw_weight": draw_weight,
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
    draw_weight: float,
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
            "draw_weight": draw_weight,
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
    prevalence: dict[str, float],
    design_share: dict[str, float],
) -> list[dict[str, object]]:
    bucket_quota = _bucket_share(n, len(CANONICAL_BUCKETS))
    effective_mult = 0.0 if baseline_zero else mult
    all_draws: list[dict[str, object]] = []
    cursor = 0
    for bucket, quota in zip(CANONICAL_BUCKETS, bucket_quota, strict=True):
        bucket_rows = cast(pd.DataFrame, tracking[tracking["scenario_bucket"] == bucket])
        draw_weight = _draw_weight_for_bucket(bucket, prevalence, design_share)
        if len(bucket_rows) > 0:
            chunk = _draw_from_tracking(
                bucket_rows,
                n=quota,
                mult=effective_mult,
                rng=rng,
                alloc_mean_contacts=alloc_mean_contacts,
                start_idx=cursor,
                draw_weight=draw_weight,
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
                draw_weight=draw_weight,
            )
        all_draws.extend(chunk)
        cursor += quota
    return all_draws


def _tracking_data_hash(tracking: pd.DataFrame) -> str:
    """Deterministic content hash of the tracking frame (order-independent).

    Used only as a manifest provenance fingerprint (IMP-C08 "preventing
    silent prevalence drift"): prevalence is always recomputed fresh from
    ``tracking`` in the same call, so there is no separate cache that could
    go stale against this hash — the hash documents *which* data produced the
    recorded prevalence, for audit / reproducibility, not a cache-invalidation
    check.
    """
    if tracking.empty:
        return hashlib.sha256(b"empty").hexdigest()
    row_hashes = pd.util.hash_pandas_object(tracking, index=False).to_numpy()  # type: ignore[attr-defined]  # pd.util re-export missing from stubs
    return hashlib.sha256(np.sort(row_hashes).tobytes()).hexdigest()


def run_monte_carlo_scenarios(
    tracking: pd.DataFrame,
    allocation_path: Path | None,
    *,
    out_dir: Path,
    shock_multiplier: float | None = None,
    baseline_shock_zero: bool = False,
    n_draws: int | None = None,
) -> dict[str, object]:
    """Stratified MC draws across all canonical buckets, with importance weights.

    Draws are allocated in equal thirds across the canonical scenario buckets
    (a variance-reduction design), then every draw is stamped with a
    ``draw_weight = empirical_prevalence(bucket) / design_share(bucket)`` so
    pooled statistics across buckets can be corrected back to the observed
    scenario mix (see :func:`weighted_pooled_mean`,
    :func:`weighted_pooled_quantile`). Prevalence is recomputed fresh from
    ``tracking`` on every call.

    Args:
        tracking: Cleaned tracking-wave rows with ``shock_score_s`` and
            ``scenario_bucket`` attached.
        allocation_path: Path to a Module B ``allocation_output`` parquet
            (for the B->C handshake), or ``None``.
        out_dir: Directory to write ``monte_carlo_draws.parquet``,
            ``monte_carlo_shock_catalog.yaml``, and
            ``scenario_run_manifest.json`` into.
        shock_multiplier: Override for ``shock_params.yaml:shock_multiplier``.
        baseline_shock_zero: Force every draw's shock score to zero (baseline
            scenario ablation).
        n_draws: Override for the draw budget (``_mc_n()`` when omitted).

    Returns:
        The run manifest: draw budget, seed, bucket quotas, empirical
        prevalences, design shares, and the tracking-data hash they were
        computed from.

    Raises:
        ValueError: If ``tracking`` lacks ``shock_score_s``, or a canonical
            bucket is absent from both ``tracking`` and
            ``shock_params.yaml:bucket_priors``.

    Example:
        >>> manifest = run_monte_carlo_scenarios(  # doctest: +SKIP
        ...     tracking, None, out_dir=Path("/tmp/mc"), n_draws=600
        ... )
        >>> manifest["n_draws"]  # doctest: +SKIP
        600
    """
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

    prevalence = empirical_bucket_prevalence(tracking)
    design_share = _design_shares(n)

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
        prevalence,
        design_share,
    )

    draws_df = pd.DataFrame(all_draws)
    validate_dataframe_contract(draws_df, "monte_carlo_draws")
    draws_df.to_parquet(out_dir / "monte_carlo_draws.parquet", index=False)

    bucket_quota = _bucket_share(n, len(CANONICAL_BUCKETS))
    manifest = _build_scenario_manifest(
        tracking=tracking,
        n=n,
        mult=mult,
        baseline_zero=baseline_zero,
        allocation_path=allocation_path,
        bucket_quota=bucket_quota,
        prevalence=prevalence,
        design_share=design_share,
    )
    (out_dir / "scenario_run_manifest.json").write_text(json.dumps(manifest, indent=2))
    # Math sanity: each bucket quota sums to n.
    assert sum(bucket_quota) == n
    assert math.isclose(sum(bucket_quota), n)
    return manifest


def _build_scenario_manifest(
    *,
    tracking: pd.DataFrame,
    n: int,
    mult: float,
    baseline_zero: bool,
    allocation_path: Path | None,
    bucket_quota: list[int],
    prevalence: dict[str, float],
    design_share: dict[str, float],
) -> dict[str, object]:
    """Assemble the ``scenario_run_manifest.json`` payload for one MC run."""
    buckets_synthesised = [
        b for b in CANONICAL_BUCKETS if len(tracking[tracking["scenario_bucket"] == b]) == 0
    ]
    draw_weights = {
        b: _draw_weight_for_bucket(b, prevalence, design_share) for b in CANONICAL_BUCKETS
    }
    return {
        "n_draws": n,
        "seed": 42,
        "shock_multiplier": mult,
        "baseline_shock_zero": baseline_zero,
        "allocation_input": str(allocation_path) if allocation_path else None,
        "canonical_buckets": list(CANONICAL_BUCKETS),
        "bucket_quotas": dict(zip(CANONICAL_BUCKETS, bucket_quota, strict=True)),
        "buckets_synthesised_from_prior": buckets_synthesised,
        "bucket_prevalence_observed": prevalence,
        "bucket_design_share": design_share,
        "bucket_draw_weight": draw_weights,
        "tracking_data_hash": _tracking_data_hash(tracking),
        "repo_root": str(repo_root()),
        "created_at_utc": datetime.now(tz=UTC).isoformat(),
    }

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Walk-forward out-of-sample validation for the hierarchical tracking model.

For each chronologically-ordered holdout poll ``k`` (starting from
``min_train_size``), the tracking model is refit on polls ``[0..k-1]``
and the posterior latent margin at the holdout poll's date is used to
predict the held-out observation. Reported metrics:

* **Brier score / log loss** — binary task ``P(margin > 0)`` vs. observed
  sign of the held-out poll margin.
* **80% / 95% interval coverage** — fraction of held-out poll margins
  whose observed value falls inside the posterior HDI on the holdout date.

The Paraguay 2018 fixture provides only four tracking polls, so the
walk-forward loop is small (two holdouts at ``min_train_size=2``). This
is documented in the metrics summary as a data sparsity caveat, not a
methodology limitation; the same routine scales to denser polling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import cast

import arviz as az
import numpy as np
import pandas as pd

from module_c_forecasting_scenarios.models.tracking.hierarchical import (
    _build_day_index,  # pyright: ignore[reportPrivateUsage]
    fit_tracking_hierarchical,
)

_EPS = 1e-6


@dataclass(frozen=True)
class WalkForwardResult:
    """Per-holdout predictions plus aggregate metrics.

    Attributes:
        per_holdout: DataFrame with one row per held-out poll containing
            ``poll_wave_id``, ``publication_date``, ``observed_margin_pp``,
            ``predicted_posterior_mean_pp``, ``hdi80_low_pp``, ``hdi80_high_pp``,
            ``hdi95_low_pp``, ``hdi95_high_pp``, ``prob_margin_positive``,
            ``observed_positive``, ``in_hdi80``, ``in_hdi95``.
        metrics: Dict with ``brier_score``, ``log_loss``,
            ``coverage_80pct``, ``coverage_95pct``, ``n_holdouts``.
        min_train_size: Smallest training fold size used.
        calibration_series: Series tag forwarded from input.
    """

    per_holdout: pd.DataFrame
    metrics: dict[str, float] = field(default_factory=dict)
    min_train_size: int = 2
    calibration_series: str = "A"


def _hdi_bounds(samples: np.ndarray, hdi_prob: float) -> tuple[float, float]:
    hdi = az.hdi(samples, hdi_prob=hdi_prob)
    arr = np.asarray(hdi).reshape(-1)
    return float(arr[0]), float(arr[1])


def _predict_holdout(
    train: pd.DataFrame,
    holdout_row: pd.Series,
    *,
    outcome_event_date: date,
    calibration_series: str,
) -> dict[str, float]:
    """Fit on ``train`` and extract posterior of latent margin at holdout's date."""
    idata = fit_tracking_hierarchical(
        train,
        outcome_event_date=outcome_event_date,
        calibration_series=calibration_series,
    )

    days, _ = _build_day_index(train, outcome_event_date)
    fs = pd.to_datetime(holdout_row["field_window_start"])
    fe = pd.to_datetime(holdout_row["field_window_end"])
    mid_ts = pd.Timestamp(cast(object, fs + (fe - fs) / 2))  # type: ignore[arg-type]
    if pd.isna(mid_ts):
        raise ValueError(f"holdout {holdout_row.get('poll_wave_id')!r} has NaT field window")
    mid_date = mid_ts.date()

    day_strs = [pd.Timestamp(cast(object, d)).strftime("%Y-%m-%d") for d in days]  # type: ignore[arg-type]
    end_d = pd.Timestamp(cast(object, days[-1])).date()  # type: ignore[arg-type]
    start_d = pd.Timestamp(cast(object, days[0])).date()  # type: ignore[arg-type]
    clamped = max(min(mid_date, end_d), start_d)
    day_label = clamped.strftime("%Y-%m-%d")
    day_idx = day_strs.index(day_label)

    post = cast(object, idata.posterior["mu_margin"])  # type: ignore[union-attr]
    samples = np.asarray(post.isel(day=day_idx).values).reshape(-1)  # type: ignore[attr-defined]

    hdi80_low, hdi80_high = _hdi_bounds(samples, hdi_prob=0.80)
    hdi95_low, hdi95_high = _hdi_bounds(samples, hdi_prob=0.95)
    prob_pos = float((samples > 0.0).mean())
    return {
        "predicted_posterior_mean_pp": float(samples.mean()),
        "hdi80_low_pp": hdi80_low,
        "hdi80_high_pp": hdi80_high,
        "hdi95_low_pp": hdi95_low,
        "hdi95_high_pp": hdi95_high,
        "prob_margin_positive": prob_pos,
    }


def walk_forward_tracking_validation(
    tracking: pd.DataFrame,
    *,
    outcome_event_date: date,
    calibration_series: str,
    min_train_size: int = 2,
) -> WalkForwardResult:
    """Refit the hierarchical tracking model leave-one-future-out.

    Args:
        tracking: Cleaned tracking poll frame (output of ``clean_raw_polls``).
            Must include ``publication_date``, ``field_window_*``, ``m_poll_pp``,
            ``poll_wave_id``, ``pollster_id``, ``phi_transparency``.
        outcome_event_date: Outcome anchor (April 22, 2018 for Paraguay).
        calibration_series: ``"A"`` or ``"B"`` calibration anchor identifier.
        min_train_size: Minimum number of polls in the training fold before
            the first holdout. The random-walk likelihood is degenerate with
            a single poll, so ``2`` is the practical floor.

    Returns:
        WalkForwardResult containing per-holdout predictions and aggregate
        Brier / log-loss / coverage metrics.

    Raises:
        ValueError: If ``tracking`` has fewer rows than ``min_train_size + 1``.

    Example:
        ``walk_forward_tracking_validation(tracking, outcome_event_date=date(2018,4,22),
        calibration_series="A")`` returns a result with 2 holdouts for the
        Paraguay 2018 fixture (4 tracking polls).
    """
    if len(tracking) < min_train_size + 1:
        raise ValueError(
            f"need at least {min_train_size + 1} polls for walk-forward; got {len(tracking)}"
        )

    ordered = tracking.sort_values("publication_date").reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for k in range(min_train_size, len(ordered)):
        train = ordered.iloc[:k].copy()
        holdout = ordered.iloc[k]
        obs = float(holdout["m_poll_pp"])
        pred = _predict_holdout(
            train,
            holdout,
            outcome_event_date=outcome_event_date,
            calibration_series=calibration_series,
        )
        in_hdi80 = bool(pred["hdi80_low_pp"] <= obs <= pred["hdi80_high_pp"])
        in_hdi95 = bool(pred["hdi95_low_pp"] <= obs <= pred["hdi95_high_pp"])
        rows.append(
            {
                "fold": k - min_train_size + 1,
                "poll_wave_id": str(holdout["poll_wave_id"]),
                "publication_date": pd.Timestamp(holdout["publication_date"]).date(),
                "n_train": k,
                "observed_margin_pp": obs,
                "observed_positive": int(obs > 0.0),
                **pred,
                "in_hdi80": in_hdi80,
                "in_hdi95": in_hdi95,
            }
        )

    per_holdout = pd.DataFrame(rows)
    metrics = summarize_walk_forward(per_holdout)
    return WalkForwardResult(
        per_holdout=per_holdout,
        metrics=metrics,
        min_train_size=min_train_size,
        calibration_series=calibration_series,
    )


def summarize_walk_forward(per_holdout: pd.DataFrame) -> dict[str, float]:
    """Aggregate Brier / log-loss / coverage metrics from per-holdout predictions.

    Args:
        per_holdout: DataFrame produced by :func:`walk_forward_tracking_validation`.

    Returns:
        Dict with ``brier_score``, ``log_loss``, ``coverage_80pct``,
        ``coverage_95pct``, ``n_holdouts``.

    Raises:
        KeyError: If required columns are absent from ``per_holdout``.

    Example:
        ``summarize_walk_forward(result.per_holdout)`` returns the same dict
        attached to ``result.metrics``.
    """
    if per_holdout.empty:
        return {
            "brier_score": float("nan"),
            "log_loss": float("nan"),
            "coverage_80pct": float("nan"),
            "coverage_95pct": float("nan"),
            "n_holdouts": 0.0,
        }
    p = per_holdout["prob_margin_positive"].to_numpy(dtype=np.float64)
    p_clip = np.clip(p, _EPS, 1.0 - _EPS)
    y = per_holdout["observed_positive"].to_numpy(dtype=np.float64)
    brier = float(np.mean((p - y) ** 2))
    log_loss = float(-np.mean(y * np.log(p_clip) + (1.0 - y) * np.log(1.0 - p_clip)))
    cov80 = float(per_holdout["in_hdi80"].mean())
    cov95 = float(per_holdout["in_hdi95"].mean())
    return {
        "brier_score": brier,
        "log_loss": log_loss,
        "coverage_80pct": cov80,
        "coverage_95pct": cov95,
        "n_holdouts": float(len(per_holdout)),
    }

"""Posterior predictive check pipeline for Module C tracking model.

Example::

    poetry run python -m module_c_forecasting_scenarios.pipeline.run_ppc \\
        --raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \\
        --out-dir data/processed/module_c/ppc
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path

import numpy as np
import yaml

from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.mlflow_tracking import log_run_params
from module_c_forecasting_scenarios.models.tracking.hierarchical import (
    _build_day_index,  # pyright: ignore[reportPrivateUsage]
    fit_tracking_hierarchical,
)
from module_c_forecasting_scenarios.paths import module_config_dir
from module_c_forecasting_scenarios.viz.ppc_plot import generate_ppc_plot

logger = logging.getLogger(__name__)


def calibration_verdict_from_coverage(cov80: float, cov95: float) -> str:
    """Map empirical PPC interval coverages to a calibration verdict.

    Both interval levels must behave: a 95% band wide enough to cover
    everything is not "calibrated" when the 80% band misses badly (the former
    rubric labelled exactly that case calibrated).

    Args:
        cov80: Fraction of observations inside the 80% predictive interval.
        cov95: Fraction of observations inside the 95% predictive interval.

    Returns:
        One of ``calibrated``, ``under-confident``, ``miscalibrated-shape``,
        ``slightly-over-confident``, ``over-confident``, ``prior-dominated``.
    """
    if cov80 == 0.0 and cov95 == 0.0:
        return "prior-dominated"
    if cov95 >= 0.90 and 0.60 <= cov80 <= 0.95:
        return "calibrated"
    if cov95 >= 0.90 and cov80 > 0.95:
        return "under-confident"
    if cov95 >= 0.90:
        return "miscalibrated-shape"
    if cov95 >= 0.70:
        return "slightly-over-confident"
    return "over-confident"


def run_ppc(
    tracking_csv: Path,
    out_dir: Path,
    *,
    calibration_yaml: Path | None = None,
) -> dict[str, object]:
    """Fit tracking model with PPC sampling and write plot + summary.

    Args:
        tracking_csv: Path to raw polls CSV.
        out_dir: Directory for all outputs.
        calibration_yaml: Override calibration config path.

    Returns:
        Summary dict logged to MLflow and written as ``ppc_summary.json``.
    """
    cal_path = calibration_yaml or (module_config_dir() / "calibration.yaml")
    with open(cal_path) as f:
        cal = yaml.safe_load(f)
    series = str(cal["series"]).strip().upper()
    outcome = date.fromisoformat(str(cal.get("outcome_event_date", "2018-04-22")))

    raw = load_raw_polls_csv(tracking_csv)
    tracking, _ = clean_raw_polls(raw, series)

    # PPC runs against the production model, anchor included when configured.
    m_star = float(cal["anchors"][series]["margin_m_star_pp"])
    use_anchor = bool(cal.get("use_outcome_anchor", True))
    idata = fit_tracking_hierarchical(
        tracking,
        outcome_event_date=outcome,
        calibration_series=series,
        sample_ppc=True,
        m_star_pp=m_star if use_anchor else None,
        anchor_sigma_pp=float(cal.get("outcome_anchor_sigma_pp", 0.5)),
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / "ppc_plot.png"
    generate_ppc_plot(idata, tracking, png_path)
    logger.info("PPC plot written to %s", png_path)

    # --- calibration summary ---
    ppc_samples = np.asarray(
        idata.posterior_predictive["obs"].values  # type: ignore[union-attr]
    ).reshape(-1, len(tracking))

    sorted_df = tracking.sort_values("publication_date")
    orig_idx = sorted_df.index.to_numpy()
    obs = sorted_df["m_poll_pp"].to_numpy(dtype=np.float64)
    ppc_ordered = ppc_samples[:, orig_idx]  # shape: (n_samples, n_polls)

    # HDI via symmetric percentiles (avoids az.hdi 2D ambiguity)
    low80 = np.percentile(ppc_ordered, 10.0, axis=0)
    high80 = np.percentile(ppc_ordered, 90.0, axis=0)
    low95 = np.percentile(ppc_ordered, 2.5, axis=0)
    high95 = np.percentile(ppc_ordered, 97.5, axis=0)

    in80 = int(np.sum((obs >= low80) & (obs <= high80)))
    in95 = int(np.sum((obs >= low95) & (obs <= high95)))
    n = len(obs)
    cov80 = in80 / n
    cov95 = in95 / n

    calibration_verdict = calibration_verdict_from_coverage(cov80, cov95)

    _, poll_day_idx = _build_day_index(tracking, outcome)
    days_spanned = int(poll_day_idx.max() - poll_day_idx.min()) if len(poll_day_idx) > 1 else 0

    summary: dict[str, object] = {
        "calibration_series": series,
        "outcome_event_date": outcome.isoformat(),
        "n_tracking_polls": n,
        "days_spanned": days_spanned,
        "ppc_coverage_80pct": cov80,
        "ppc_coverage_95pct": cov95,
        "polls_in_80pct_hdi": in80,
        "polls_in_95pct_hdi": in95,
        "calibration_verdict": calibration_verdict,
        "ppc_plot_path": str(png_path),
    }
    (out_dir / "ppc_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    log_run_params(summary)
    logger.info("PPC summary: %s", summary)
    return summary


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Module C — posterior predictive checks")
    p.add_argument("--raw-csv", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--calibration-yaml", type=Path, default=None)
    args = p.parse_args(argv)
    run_ppc(args.raw_csv, args.out_dir, calibration_yaml=args.calibration_yaml)


if __name__ == "__main__":
    main()

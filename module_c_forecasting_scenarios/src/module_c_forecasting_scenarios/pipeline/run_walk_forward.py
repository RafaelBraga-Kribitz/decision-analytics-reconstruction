"""Walk-forward validation runner for Module C tracking model.

Example::

    poetry run python -m module_c_forecasting_scenarios.pipeline.run_walk_forward \\
        --raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \\
        --out-dir data/processed/module_c/walk_forward
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path
from typing import cast

import yaml

from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.mlflow_tracking import log_run_params
from module_c_forecasting_scenarios.paths import module_config_dir
from module_c_forecasting_scenarios.validation.walk_forward import (
    walk_forward_tracking_validation,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    """Run walk-forward validation and emit per-holdout + metrics artifacts.

    Args:
        argv: Optional argv override (CLI uses ``sys.argv`` when omitted).

    Returns:
        None. Writes ``walk_forward_per_holdout.parquet`` and
        ``walk_forward_metrics.json`` under ``--out-dir``.

    Raises:
        ValueError: Propagated when input data is too sparse for the
            requested ``--min-train-size``.

    Example:
        ``python -m module_c_forecasting_scenarios.pipeline.run_walk_forward
        --raw-csv ... --out-dir ...``
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Module C — walk-forward validation")
    p.add_argument("--raw-csv", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--calibration-yaml", type=Path, default=None)
    p.add_argument("--min-train-size", type=int, default=2)
    args = p.parse_args(argv)

    cal_path = args.calibration_yaml or (module_config_dir() / "calibration.yaml")
    with open(cal_path) as f:
        cal = yaml.safe_load(f)
    series = str(cal["series"]).strip().upper()
    outcome = date.fromisoformat(str(cal.get("outcome_event_date", "2018-04-22")))

    raw = load_raw_polls_csv(args.raw_csv)
    tracking, _ = clean_raw_polls(raw, series)
    if len(tracking) < args.min_train_size + 1:
        raise ValueError(
            f"insufficient tracking polls ({len(tracking)}) for "
            f"min_train_size={args.min_train_size}; need at least "
            f"{args.min_train_size + 1}"
        )

    result = walk_forward_tracking_validation(
        tracking,
        outcome_event_date=outcome,
        calibration_series=series,
        min_train_size=args.min_train_size,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    per_path = args.out_dir / "walk_forward_per_holdout.parquet"
    result.per_holdout.to_parquet(per_path, index=False)
    metrics_path = args.out_dir / "walk_forward_metrics.json"
    payload = {
        "calibration_series": series,
        "outcome_event_date": outcome.isoformat(),
        "min_train_size": int(args.min_train_size),
        "n_total_polls": int(len(tracking)),
        **result.metrics,
    }
    metrics_path.write_text(json.dumps(payload, indent=2, default=str))
    log_run_params(cast(dict[str, object], payload))
    logger.info("walk-forward complete -> %s", args.out_dir)


if __name__ == "__main__":
    main()

"""Monte Carlo scenarios + shock catalog."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import yaml

from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.paths import module_config_dir
from module_c_forecasting_scenarios.scenarios.monte_carlo import run_monte_carlo_scenarios

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Module C — Monte Carlo scenarios")
    p.add_argument("--raw-csv", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--allocation-parquet", type=Path, default=None)
    p.add_argument("--baseline-shock-zero", action="store_true")
    args = p.parse_args(argv)
    with open(module_config_dir() / "calibration.yaml") as f:
        cal = yaml.safe_load(f)
    series = str(cal["series"]).strip().upper()
    raw = load_raw_polls_csv(args.raw_csv)
    tracking, _ = clean_raw_polls(raw, series)
    run_monte_carlo_scenarios(
        tracking,
        args.allocation_parquet,
        out_dir=args.out_dir,
        baseline_shock_zero=args.baseline_shock_zero,
    )
    logger.info("monte carlo complete -> %s", args.out_dir)


if __name__ == "__main__":
    main()

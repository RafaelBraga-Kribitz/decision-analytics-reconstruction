"""Orchestrate tracking → exit → Monte Carlo → battleground + Quarto copy."""

from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path

import pandas as pd
import yaml

from module_c_forecasting_scenarios.geo.heatmap import export_battleground_department_table
from module_c_forecasting_scenarios.paths import module_config_dir, repo_root
from module_c_forecasting_scenarios.pipeline.run_exit import main as run_exit_main
from module_c_forecasting_scenarios.pipeline.run_monte_carlo import main as run_monte_carlo_main
from module_c_forecasting_scenarios.pipeline.run_tracking import main as run_tracking_main

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Module C — full pipeline")
    p.add_argument("--raw-csv", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--allocation-parquet", type=Path, default=None)
    args = p.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    run_tracking_main(["--raw-csv", str(args.raw_csv), "--out-dir", str(args.out_dir / "tracking")])
    run_exit_main(["--raw-csv", str(args.raw_csv), "--out-dir", str(args.out_dir / "exit")])
    mc_argv = [
        "--raw-csv",
        str(args.raw_csv),
        "--out-dir",
        str(args.out_dir / "mc"),
    ]
    if args.allocation_parquet:
        mc_argv += ["--allocation-parquet", str(args.allocation_parquet)]
    run_monte_carlo_main(mc_argv)
    with open(module_config_dir() / "calibration.yaml") as f:
        series = str(yaml.safe_load(f)["series"]).strip().upper()
    daily = pd.read_parquet(args.out_dir / "tracking" / "daily_posterior_forecast.parquet")
    export_battleground_department_table(
        daily,
        args.out_dir / "battleground" / "battleground_department_probability.parquet",
        calibration_series=series,
    )
    qsrc = repo_root() / "module_c_forecasting_scenarios/portfolio/quarto/post_mortem.qmd"
    qdst = args.out_dir / "post_mortem.qmd"
    if qsrc.exists():
        shutil.copy(qsrc, qdst)
    logger.info("run_all complete -> %s (render Quarto manually: quarto render %s)", args.out_dir, qdst)


if __name__ == "__main__":
    main()

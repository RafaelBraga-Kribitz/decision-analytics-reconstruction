"""Exit / quick-count bias stage."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd
import yaml

from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.contract_validate import validate_dataframe_contract
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.models.exit.exit_model import fit_exit_quickcount
from module_c_forecasting_scenarios.paths import module_config_dir

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Module C — exit bias pipeline")
    p.add_argument("--raw-csv", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)
    with open(module_config_dir() / "calibration.yaml") as f:
        cal = yaml.safe_load(f)
    series = str(cal["series"]).strip().upper()
    raw = load_raw_polls_csv(args.raw_csv)
    _, exit_df = clean_raw_polls(raw, series)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if exit_df.empty:
        logger.warning("no exit rows in raw feed")
        pd.DataFrame([{"note": "no_exit_rows"}]).to_parquet(
            args.out_dir / "exit_model_summary.parquet", index=False
        )
        (args.out_dir / "run_exit_manifest.json").write_text(
            json.dumps({"calibration_series": series, "n_exit_rows": 0}, indent=2)
        )
        return
    validate_dataframe_contract(exit_df, "polls_clean_exit_wave")
    summary, _idata = fit_exit_quickcount(exit_df, calibration_series=series)
    summary.to_parquet(args.out_dir / "exit_model_summary.parquet", index=False)
    (args.out_dir / "run_exit_manifest.json").write_text(
        json.dumps({"calibration_series": series, "n_exit_rows": len(exit_df)}, indent=2)
    )
    logger.info("exit stage complete -> %s", args.out_dir)


if __name__ == "__main__":
    main()

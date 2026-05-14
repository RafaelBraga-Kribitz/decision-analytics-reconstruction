"""Run tracking ETL + hierarchical fit + daily / house exports."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path
from typing import cast

import yaml

from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.contract_validate import validate_dataframe_contract
from module_c_forecasting_scenarios.data.emitters import (
    build_house_effect_seed_matrix,
    build_polling_transparency_audit,
)
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.mlflow_tracking import log_run_params
from module_c_forecasting_scenarios.models.tracking.hierarchical import run_tracking_fit_and_export
from module_c_forecasting_scenarios.paths import module_config_dir, repo_root
from module_c_forecasting_scenarios.viz.plotly_explorer import write_scenario_explorer_html

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Module C — tracking pipeline")
    p.add_argument("--raw-csv", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--calibration-yaml", type=Path, default=None)
    args = p.parse_args(argv)
    cal_path = args.calibration_yaml or (module_config_dir() / "calibration.yaml")
    with open(cal_path) as f:
        cal = yaml.safe_load(f)
    series = str(cal["series"]).strip().upper()
    outcome = date.fromisoformat(str(cal.get("outcome_event_date", "2018-04-22")))
    m_star = float(cal["anchors"][series]["margin_m_star_pp"])
    raw = load_raw_polls_csv(args.raw_csv)
    tracking, exit_df = clean_raw_polls(raw, series)
    validate_dataframe_contract(tracking, "polls_clean_tracking_wave")
    if len(exit_df):
        validate_dataframe_contract(exit_df, "polls_clean_exit_wave")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    seed = build_house_effect_seed_matrix(tracking, m_star, series)
    seed.to_csv(args.out_dir / "house_effect_seed_matrix.csv", index=False)
    audit = build_polling_transparency_audit(tracking)
    audit.to_csv(args.out_dir / "polling_transparency_audit.csv", index=False)
    _, daily, houses = run_tracking_fit_and_export(
        tracking,
        args.out_dir,
        outcome_event_date=outcome,
        calibration_series=series,
    )
    validate_dataframe_contract(daily, "daily_posterior_forecast")
    validate_dataframe_contract(houses, "posterior_house_effects")
    write_scenario_explorer_html(daily, tracking, args.out_dir / "scenario_explorer.html")
    manifest = {
        "calibration_series": series,
        "m_star_pp": m_star,
        "outcome_event_date": outcome.isoformat(),
        "repo_root": str(repo_root()),
        "n_tracking_waves": len(tracking),
    }
    (args.out_dir / "run_tracking_manifest.json").write_text(json.dumps(manifest, indent=2))
    log_run_params(cast(dict[str, object], manifest))
    logger.info("wrote outputs under %s", args.out_dir)


if __name__ == "__main__":
    main()

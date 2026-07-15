"""Leave-one-wave-out (LOWO) validation runner for the Module C tracking model.

Example::

    MLFLOW_TRACKING_URI=file:./mlruns \\
    poetry run python -m module_c_forecasting_scenarios.pipeline.run_lowo \\
        --raw-csv module_c_forecasting_scenarios/tests/fixtures/polls_raw_fixture.csv \\
        --out-dir data/processed/module_c/lowo \\
        --summary-json reports/module_c_lowo_metrics.json

``--out-dir`` receives the full per-wave parquet plus a metrics JSON (under the
gitignored ``data/processed`` tree). ``--summary-json`` optionally writes a
committed, self-contained summary (metrics + per-wave records) for
``reports/VALIDATION.md`` to cite.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from datetime import date
from pathlib import Path
from typing import cast

import yaml

from module_c_forecasting_scenarios.config import load_sampler_config
from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.mlflow_tracking import log_run_params
from module_c_forecasting_scenarios.paths import module_config_dir
from module_c_forecasting_scenarios.validation.leave_one_wave_out import (
    leave_one_wave_out_validation,
)

logger = logging.getLogger(__name__)


def _sampler_disclosure(overrides: dict[str, object] | None) -> dict[str, object]:
    """Describe the sampler config the fits will actually use, for the artifact.

    Mirrors ``hierarchical._sampler_kwargs``: any non-empty ``MC_FAST`` value
    (including ``"0"`` — see issue #60) selects the reduced fast path; explicit
    CLI ``overrides`` are then applied on top, exactly as the fit applies them.
    The committed summary must disclose which config produced the numbers.
    """
    cfg = load_sampler_config()
    if os.environ.get("MC_FAST"):
        base: dict[str, object] = {
            "sampler_path": "reduced-draw fast path (MC_FAST set)",
            "chains": 2,
            "draws_per_chain": int(cfg["draws_fast"]),
            "tune": int(cfg["tune_fast"]),
            "target_accept": float(cfg.get("target_accept", 0.9)),
            "random_seed": int(cfg.get("random_seed", 42)),
        }
    else:
        base = {
            "sampler_path": "full NUTS (v0.4 gates)",
            "chains": int(cfg.get("chains", 4)),
            "draws_per_chain": int(cfg.get("draws", 1000)),
            "tune": int(cfg.get("tune", 1000)),
            "target_accept": float(cfg.get("target_accept_full", cfg.get("target_accept", 0.95))),
            "max_treedepth": int(cfg.get("max_treedepth", 10)),
            "random_seed": int(cfg.get("random_seed", 42)),
        }
    if overrides:
        applied = {k: v for k, v in overrides.items() if v is not None}
        if applied:
            base["sampler_path"] = str(base["sampler_path"]) + " with explicit CLI overrides"
            if "draws" in applied:
                base["draws_per_chain"] = applied.pop("draws")
            base.update(applied)
            base["cli_overrides"] = sorted(k for k, v in overrides.items() if v is not None)
    return base


def main(argv: list[str] | None = None) -> None:
    """Run LOWO validation and emit per-wave + metrics artifacts.

    Args:
        argv: Optional argv override (CLI uses ``sys.argv`` when omitted).

    Returns:
        None. Writes ``lowo_per_wave.parquet`` and ``lowo_metrics.json`` under
        ``--out-dir``, and (if given) a committed summary at ``--summary-json``.

    Raises:
        ValueError: Propagated when the fixture has fewer than 3 tracking waves.

    Example:
        ``python -m module_c_forecasting_scenarios.pipeline.run_lowo
        --raw-csv ... --out-dir ...``
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Module C — leave-one-wave-out validation")
    p.add_argument("--raw-csv", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--calibration-yaml", type=Path, default=None)
    p.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="Optional committed summary (metrics + per-wave records) JSON path.",
    )
    p.add_argument(
        "--chains",
        type=int,
        default=None,
        help="Explicit pm.sample chains override (disclosed in the artifact).",
    )
    p.add_argument(
        "--draws",
        type=int,
        default=None,
        help="Explicit pm.sample draws-per-chain override (disclosed in the artifact).",
    )
    p.add_argument(
        "--tune",
        type=int,
        default=None,
        help="Explicit pm.sample tune override (disclosed in the artifact).",
    )
    args = p.parse_args(argv)

    sampler_overrides: dict[str, object] | None = None
    if any(v is not None for v in (args.chains, args.draws, args.tune)):
        sampler_overrides = {"chains": args.chains, "draws": args.draws, "tune": args.tune}

    cal_path = args.calibration_yaml or (module_config_dir() / "calibration.yaml")
    with open(cal_path) as f:
        cal = yaml.safe_load(f)
    series = str(cal["series"]).strip().upper()
    outcome = date.fromisoformat(str(cal.get("outcome_event_date", "2018-04-22")))

    raw = load_raw_polls_csv(args.raw_csv)
    tracking, _ = clean_raw_polls(raw, series)
    if len(tracking) < 3:
        raise ValueError(
            f"insufficient tracking waves ({len(tracking)}) for leave-one-wave-out; "
            f"need at least 3"
        )

    t0 = time.time()
    result = leave_one_wave_out_validation(
        tracking,
        outcome_event_date=outcome,
        calibration_series=series,
        sampler_overrides=sampler_overrides,
    )
    runtime_s = time.time() - t0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    per_path = args.out_dir / "lowo_per_wave.parquet"
    result.per_wave.to_parquet(per_path, index=False)

    payload: dict[str, object] = {
        "validation": "leave_one_wave_out",
        "model_variant": result.model_variant,
        "calibration_series": series,
        "election_date": outcome.isoformat(),
        "n_total_tracking_waves": int(len(tracking)),
        "runtime_seconds": round(runtime_s, 1),
        "sampler": _sampler_disclosure(sampler_overrides),
        "caveat": (
            "Out-of-sample predictive performance on 8 waves of one election "
            "(Paraguay 2018) — NOT validated forecasting skill. Unanchored "
            "likelihood path: the verified TSJE margin never enters any fold's fit."
        ),
        **result.metrics,
    }
    metrics_path = args.out_dir / "lowo_metrics.json"
    metrics_path.write_text(json.dumps(payload, indent=2, default=str))
    log_run_params(cast(dict[str, object], payload))

    if args.summary_json is not None:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            **payload,
            "per_wave": result.per_wave.to_dict(orient="records"),
        }
        args.summary_json.write_text(json.dumps(summary, indent=2, default=str))
        logger.info("LOWO committed summary -> %s", args.summary_json)

    logger.info("leave-one-wave-out complete -> %s", args.out_dir)


if __name__ == "__main__":
    main()

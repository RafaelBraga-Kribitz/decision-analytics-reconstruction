"""
Contract-aligned batch export for Module A.

Usage:
    python -m population_segmentation.pipeline.export \
        --config module_a_population_segmentation/config/generation.yaml \
        --anchors module_a_population_segmentation/config/calibration_anchors.yaml \
        --out-dir data/processed \
        [--sample-size 50000]

Produces (all under --out-dir):
    population_master_clean.parquet
    segment_labels.parquet
    participation_propensity.parquet
    media_reachability_by_segment.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def run_export(
    config: dict[str, Any],
    anchors: dict[str, Any],
    out_dir: Path,
    sample_size: int | None = None,
) -> dict[str, Path]:
    """Execute the full Module A pipeline and write contract artifacts.

    Parameters
    ----------
    config:
        Generation config dict (from generation.yaml).
    anchors:
        Calibration anchors dict (from calibration_anchors.yaml).
    out_dir:
        Directory to write all four artifacts.
    sample_size:
        Override the sample_size in config when provided.

    Returns
    -------
    dict mapping artifact name to written Path.
    """
    from population_segmentation.data.cleaner import clean_population
    from population_segmentation.data.generator import generate_population
    from population_segmentation.data.raw_injector import inject_flaws
    from population_segmentation.data.segment_reachability_aggregate import (
        aggregate_media_reachability_by_segment,
    )
    from population_segmentation.features.behavioral import build_behavioral_features
    from population_segmentation.features.demographic import build_demographic_features
    from population_segmentation.features.reachability import build_reachability_features
    from population_segmentation.models.propensity import PropensityModel
    from population_segmentation.models.segmentation import build_segmentation_frame

    if sample_size is not None:
        config = dict(config)
        config["sample_size"] = sample_size

    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[export] Generating population (n={config['sample_size']}) ...", flush=True)
    raw = generate_population(config, seed=42)

    print("[export] Injecting flaws ...", flush=True)
    raw_dirty = inject_flaws(raw, config, seed=42)

    print("[export] Cleaning ...", flush=True)
    clean_df = clean_population(raw_dirty, config, qa_report_dir=out_dir, seed=42)

    print("[export] Building features ...", flush=True)
    feat_df = build_reachability_features(
        build_behavioral_features(build_demographic_features(clean_df))
    )

    print("[export] Segmentation ...", flush=True)
    labels_df, _seg_metrics = build_segmentation_frame(feat_df, k=6, random_state=42)

    # Use positional alignment (same row order guaranteed by build_segmentation_frame).
    # Merge-by-entity_id is unsafe when inject_flaws creates duplicate entity_ids.
    merged_feat = feat_df.reset_index(drop=True).copy()
    merged_feat["segment_label"] = labels_df["segment_label"].to_numpy()
    merged_feat["segment_id"] = labels_df["segment_id"].to_numpy()
    merged_feat["dbscan_noise_flag"] = labels_df["dbscan_noise_flag"].to_numpy()

    print("[export] Propensity model ...", flush=True)
    prop_out = PropensityModel(random_state=42).fit_predict(merged_feat, anchors)

    prop_df = pd.DataFrame(
        {
            "entity_id": merged_feat["entity_id"].to_numpy(),
            "participation_propensity": prop_out["predictions"].to_numpy(),
            "raw_logit_score": prop_out["raw_logit_score"].to_numpy(),
            "department_rake_multiplier": prop_out["department_rake_multiplier"].to_numpy(),
        }
    )

    merged_feat["participation_propensity"] = prop_df["participation_propensity"].to_numpy()

    print("[export] Aggregating media reachability ...", flush=True)
    reach_df = aggregate_media_reachability_by_segment(merged_feat)

    artifacts: dict[str, Path] = {}

    path_master = out_dir / "population_master_clean.parquet"
    merged_feat.to_parquet(path_master, index=False)
    artifacts["population_master_clean"] = path_master
    print(f"[export] Written {path_master} ({len(merged_feat)} rows)", flush=True)

    path_labels = out_dir / "segment_labels.parquet"
    labels_df[["entity_id", "segment_label", "segment_id", "dbscan_noise_flag"]].to_parquet(
        path_labels, index=False
    )
    artifacts["segment_labels"] = path_labels
    print(f"[export] Written {path_labels}", flush=True)

    path_prop = out_dir / "participation_propensity.parquet"
    prop_df.to_parquet(path_prop, index=False)
    artifacts["participation_propensity"] = path_prop
    print(f"[export] Written {path_prop}", flush=True)

    path_reach = out_dir / "media_reachability_by_segment.csv"
    reach_df.to_csv(path_reach, index=False)
    artifacts["media_reachability_by_segment"] = path_reach
    print(f"[export] Written {path_reach}", flush=True)

    # Contract validation at export exit: enforce schema invariants before returning.
    print("[export] Validating output contracts ...", flush=True)
    _validate_export_contracts(merged_feat, prop_df, labels_df, anchors)
    print("[export] Contract validation passed.", flush=True)

    return artifacts


def _validate_export_contracts(
    master: pd.DataFrame,
    prop: pd.DataFrame,
    labels: pd.DataFrame,
    anchors: dict[str, Any],
) -> None:
    """Raise ValueError if any hard contract constraint is violated.

    Checks run on the in-memory DataFrames before callers read parquet files,
    giving immediate feedback and a clear error message.
    """
    errors: list[str] = []

    # entity_id must be unique in all three artifacts
    if master["entity_id"].duplicated().any():
        n_dup = int(master["entity_id"].duplicated().sum())
        errors.append(f"population_master_clean: {n_dup} duplicate entity_id rows")
    if prop["entity_id"].duplicated().any():
        n_dup = int(prop["entity_id"].duplicated().sum())
        errors.append(f"participation_propensity: {n_dup} duplicate entity_id rows")
    if labels["entity_id"].duplicated().any():
        n_dup = int(labels["entity_id"].duplicated().sum())
        errors.append(f"segment_labels: {n_dup} duplicate entity_id rows")

    # Row counts must agree across all three artifacts
    if len(master) != len(prop):
        errors.append(f"Row count mismatch: master={len(master)}, prop={len(prop)}")
    if len(master) != len(labels):
        errors.append(f"Row count mismatch: master={len(master)}, labels={len(labels)}")

    # Propensity scores must lie in [0, 1]
    if prop["participation_propensity"].isna().any():
        errors.append("participation_propensity contains NaN values")
    elif not prop["participation_propensity"].between(0.0, 1.0).all():
        out_of_range = int((~prop["participation_propensity"].between(0.0, 1.0)).sum())
        errors.append(f"participation_propensity: {out_of_range} values outside [0, 1]")

    # Department-level calibration gate (verified TSJE anchors; ± 0.5 pp)
    dept_targets = anchors["department_participation_rates"]
    for dept in ["Presidente Hayes", "Alto Parana", "Central", "Guaira"]:
        mask = master["department"] == dept
        if mask.any():
            actual = float(prop.loc[mask.values, "participation_propensity"].mean())
            target = float(dept_targets[dept])
            if abs(actual - target) > 0.005:
                errors.append(
                    f"Department calibration gate failed: {dept} "
                    f"actual={actual:.4f} target={target:.4f} diff={actual - target:+.4f}"
                )

    # Segment labels must be from the canonical set
    from population_segmentation.models.segmentation import SEGMENT_LABEL_MAP

    valid_labels = set(SEGMENT_LABEL_MAP.values())
    bad = set(labels["segment_label"].unique()) - valid_labels
    if bad:
        errors.append(f"segment_labels contains non-canonical labels: {bad}")

    if errors:
        msg = "\n".join(f"  • {e}" for e in errors)
        raise ValueError(f"[export] Contract validation FAILED:\n{msg}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Module A contract-aligned batch export pipeline.")
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to generation.yaml",
    )
    parser.add_argument(
        "--anchors",
        required=True,
        type=Path,
        help="Path to calibration_anchors.yaml",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        type=Path,
        help="Output directory for artifacts",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Override sample_size from config (default: use config value)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    with open(args.config) as f:
        config: dict[str, Any] = yaml.safe_load(f)
    with open(args.anchors) as f:
        anchors: dict[str, Any] = yaml.safe_load(f)

    artifacts = run_export(config, anchors, args.out_dir, sample_size=args.sample_size)

    print("\n[export] Done. Artifacts written:")
    for name, path in artifacts.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main(sys.argv[1:])

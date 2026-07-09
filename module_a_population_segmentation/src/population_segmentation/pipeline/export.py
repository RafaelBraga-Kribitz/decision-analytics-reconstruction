# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
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
    media_reachability_by_segment_department.csv
    model_run_manifest.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, cast

import pandas as pd
import yaml
from contract_core import check_frame, load_named_contract

from population_segmentation.pipeline.model_run_manifest import (
    build_model_run_manifest,
    maybe_log_mlflow_export,
    write_model_run_manifest,
)

_SCHEMA_CONTRACTS_DIR: Path = Path(__file__).resolve().parents[4] / "schema_contracts"


def run_export(
    config: dict[str, Any],
    anchors: dict[str, Any],
    out_dir: Path,
    sample_size: int | None = None,
) -> dict[str, Path]:
    """Execute the full Module A batch pipeline and write contract artifacts.

    Args:
        config: Generation configuration dict (from ``generation.yaml``).
        anchors: Calibration anchors dict (from ``calibration_anchors.yaml``).
        out_dir: Directory to create (if needed) and populate with parquet/CSV/JSON
            outputs.
        sample_size: When set, overrides ``config["sample_size"]`` for this run only.

    Returns:
        Mapping logical artifact keys (for example ``population_master_clean``) to
        written :class:`~pathlib.Path` objects.

    Raises:
        Exception: Any error raised by generation, cleaning, validation, segmentation,
            or propensity steps propagates after partial console progress output.

    Example:
        From Python, after loading YAML dicts::

            paths = run_export(config, anchors, Path("data/processed"), sample_size=10_000)
    """
    from population_segmentation.data.cleaner import clean_population
    from population_segmentation.data.generator import generate_population
    from population_segmentation.data.raw_injector import inject_flaws
    from population_segmentation.data.segment_reachability_aggregate import (
        aggregate_media_reachability_by_segment,
        aggregate_media_reachability_by_segment_department,
    )
    from population_segmentation.features.behavioral import build_behavioral_features
    from population_segmentation.features.demographic import build_demographic_features
    from population_segmentation.features.reachability import build_reachability_features
    from population_segmentation.models.propensity import PropensityModel
    from population_segmentation.models.segmentation import build_segmentation_frame

    model_params_path = Path(__file__).resolve().parents[3] / "config" / "model_params.yaml"
    with open(model_params_path, encoding="utf-8") as f:
        model_params: dict[str, Any] = yaml.safe_load(f)
    stratify_by = tuple(model_params["propensity"]["stratify_by"])
    individual_spread_std = float(model_params["propensity"]["individual_spread_std"])

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
    labels_df, seg_metrics = build_segmentation_frame(feat_df, k=6, random_state=42)

    # Use positional alignment (same row order guaranteed by build_segmentation_frame).
    # Merge-by-entity_id is unsafe when inject_flaws creates duplicate entity_ids.
    merged_feat = feat_df.reset_index(drop=True).copy()
    merged_feat["segment_label"] = labels_df["segment_label"].to_numpy()
    merged_feat["segment_id"] = labels_df["segment_id"].to_numpy()
    merged_feat["dbscan_noise_flag"] = labels_df["dbscan_noise_flag"].to_numpy()

    print("[export] Propensity model ...", flush=True)
    prop_raw = PropensityModel(
        random_state=42,
        stratify_by=stratify_by,
        individual_spread_std=individual_spread_std,
    ).fit_predict(merged_feat, anchors)
    prop_out = cast(dict[str, Any], prop_raw)  # structured propensity bundle from ``fit_predict``

    prop_metrics = cast(dict[str, float], prop_out.get("metrics", {}))
    prop_df = pd.DataFrame(
        {
            "entity_id": merged_feat["entity_id"].to_numpy(),
            "participation_propensity": prop_out["predictions"].to_numpy(),
            "raw_logit_score": prop_out["raw_logit_score"].to_numpy(),
            "department_rake_multiplier": prop_out["department_rake_multiplier"].to_numpy(),
        }
    )

    merged_feat["participation_propensity"] = prop_df["participation_propensity"].to_numpy()

    print("[export] Aggregating media reachability (segment) ...", flush=True)
    reach_df = aggregate_media_reachability_by_segment(merged_feat)

    print("[export] Aggregating media reachability (segment x department) ...", flush=True)
    reach_dept_df = aggregate_media_reachability_by_segment_department(merged_feat)

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

    path_reach_dept = out_dir / "media_reachability_by_segment_department.csv"
    reach_dept_df.to_csv(path_reach_dept, index=False)
    artifacts["media_reachability_by_segment_department"] = path_reach_dept
    print(f"[export] Written {path_reach_dept}", flush=True)

    # Contract validation at export exit: enforce schema invariants before returning.
    print("[export] Validating output contracts ...", flush=True)
    _validate_export_contracts(
        merged_feat,
        prop_df,
        labels_df,
        anchors,
        reach=reach_df,
        reach_dept=reach_dept_df,
    )
    _gate_shared_core_contracts(merged_feat, prop_df, labels_df, reach_df, reach_dept_df)
    print("[export] Contract validation passed.", flush=True)

    manifest_path = out_dir / "model_run_manifest.json"
    manifest_payload = build_model_run_manifest(
        {k: v for k, v in artifacts.items()},
        random_seeds={
            "population_generation": 42,
            "raw_injection": 42,
            "cleaning": 42,
            "segmentation": 42,
            "propensity": 42,
        },
    )
    manifest_payload["segmentation_metrics"] = {
        "silhouette": float(seg_metrics.get("silhouette", 0.0)),
        "bootstrap_ari": float(seg_metrics.get("bootstrap_ari", 0.0)),
        "noise_rate": float(seg_metrics.get("noise_rate", 0.0)),
    }
    manifest_payload["propensity_metrics"] = {
        "auc_roc": float(prop_metrics.get("auc_roc", 0.0)),
        "brier_score": float(prop_metrics.get("brier_score", 0.0)),
    }
    write_model_run_manifest(manifest_path, manifest_payload)
    mlflow_metrics: dict[str, float] = {
        "segmentation_silhouette": float(seg_metrics.get("silhouette", 0.0)),
        "segmentation_bootstrap_ari": float(seg_metrics.get("bootstrap_ari", 0.0)),
        "segmentation_noise_rate": float(seg_metrics.get("noise_rate", 0.0)),
        "propensity_auc_roc": float(prop_metrics.get("auc_roc", 0.0)),
        "propensity_brier_score": float(prop_metrics.get("brier_score", 0.0)),
    }
    maybe_log_mlflow_export(manifest_payload, metrics=mlflow_metrics, local_tracking_root=out_dir)
    artifacts["model_run_manifest"] = manifest_path
    print(f"[export] Written {manifest_path}", flush=True)

    return artifacts


_VALID_REACH_CHANNELS: frozenset[str] = frozenset(
    {
        "tv",
        "radio",
        "whatsapp",
        "direct",
        "facebook_ads",
        "instagram_ads",
        "google_ads",
        "linkedin_ads",
    }
)

_MEDIA_REQUIRED_COLUMNS: tuple[str, ...] = (
    "segment_label",
    "segment_size",
    "segment_size_pct",
    "mean_participation_propensity",
    "pct_internet_access",
    "mean_tv_penetration",
    "mean_radio_penetration",
    "mean_whatsapp_penetration",
    "pct_rural",
    "pct_jopara",
    "pct_structural_dependency",
    "dominant_department",
    "primary_reach_channel",
)

_MEDIA_DEPT_REQUIRED_COLUMNS: tuple[str, ...] = (
    "segment_label",
    "department",
    "region",
    "segment_size",
    "segment_size_pct_of_department",
    "segment_size_pct_of_segment",
    "mean_participation_propensity",
    "pct_internet_access",
    "mean_tv_penetration",
    "mean_radio_penetration",
    "mean_whatsapp_penetration",
    "pct_rural",
    "pct_jopara",
    "pct_structural_dependency",
    "primary_reach_channel",
)

_VALID_REGIONS: frozenset[str] = frozenset({"ORIENTAL", "CHACO"})

_REACH_PCT_COLUMNS: tuple[str, ...] = (
    "segment_size_pct",
    "mean_participation_propensity",
    "pct_internet_access",
    "mean_tv_penetration",
    "mean_radio_penetration",
    "mean_whatsapp_penetration",
    "pct_rural",
    "pct_jopara",
    "pct_structural_dependency",
)

_CALIBRATION_DEPARTMENTS: tuple[str, ...] = (
    "Presidente Hayes",
    "Alto Parana",
    "Central",
    "Guaira",
)


def _check_duplicate_entity_ids(df: pd.DataFrame, artifact_name: str, errors: list[str]) -> None:
    if df["entity_id"].duplicated().any():
        n_dup = int(df["entity_id"].duplicated().sum())
        errors.append(f"{artifact_name}: {n_dup} duplicate entity_id rows")


def _check_row_count_alignment(
    master: pd.DataFrame, prop: pd.DataFrame, labels: pd.DataFrame, errors: list[str]
) -> None:
    if len(master) != len(prop):
        errors.append(f"Row count mismatch: master={len(master)}, prop={len(prop)}")
    if len(master) != len(labels):
        errors.append(f"Row count mismatch: master={len(master)}, labels={len(labels)}")


def _check_propensity_range(prop: pd.DataFrame, errors: list[str]) -> None:
    if bool(prop["participation_propensity"].isna().any()):
        errors.append("participation_propensity contains NaN values")
    elif not bool(prop["participation_propensity"].between(0.0, 1.0).all()):
        out_of_range = int((~prop["participation_propensity"].between(0.0, 1.0)).sum())
        errors.append(f"participation_propensity: {out_of_range} values outside [0, 1]")


def _check_department_calibration(
    master: pd.DataFrame, prop: pd.DataFrame, anchors: dict[str, Any], errors: list[str]
) -> None:
    if len(master) != len(prop):
        return
    dept_targets = anchors["department_participation_rates"]
    for dept in _CALIBRATION_DEPARTMENTS:
        mask = master["department"] == dept
        if not mask.any():
            continue
        actual = float(prop.loc[mask.values, "participation_propensity"].mean())
        target = float(dept_targets[dept])
        if abs(actual - target) > 0.005:
            errors.append(
                f"Department calibration gate failed: {dept} "
                f"actual={actual:.4f} target={target:.4f} diff={actual - target:+.4f}"
            )


def _check_pct_columns_bounded(
    df: pd.DataFrame, cols: tuple[str, ...], prefix: str, errors: list[str]
) -> None:
    for col in cols:
        if col not in df.columns:
            continue
        if bool(df[col].isna().any()):
            errors.append(f"{prefix}: {col} contains NaN")
        elif not bool(df[col].between(0.0, 1.0).all()):
            n_bad = int((~df[col].between(0.0, 1.0)).sum())
            errors.append(f"{prefix}: {col} has {n_bad} values outside [0, 1]")


def _validate_media_reachability(
    reach: pd.DataFrame, valid_labels: set[str], errors: list[str]
) -> None:
    from population_segmentation.models.segmentation import SEGMENT_LABEL_MAP

    missing_cols = [c for c in _MEDIA_REQUIRED_COLUMNS if c not in reach.columns]
    if missing_cols:
        errors.append(f"media_reachability_by_segment missing columns: {missing_cols}")
        return

    expected_k = len(SEGMENT_LABEL_MAP)
    if len(reach) != expected_k:
        errors.append(
            f"media_reachability_by_segment: expected {expected_k} rows "
            f"(one per segment), got {len(reach)}"
        )

    if reach["segment_label"].duplicated().any():
        n_dup = int(reach["segment_label"].duplicated().sum())
        errors.append(f"media_reachability_by_segment: {n_dup} duplicate segment_label rows")

    bad_reach = set(reach["segment_label"].unique()) - valid_labels
    if bad_reach:
        errors.append(f"media_reachability_by_segment: non-canonical segment labels: {bad_reach}")

    bad_channel = set(reach["primary_reach_channel"].unique()) - _VALID_REACH_CHANNELS
    if bad_channel:
        errors.append(
            f"media_reachability_by_segment: invalid primary_reach_channel values: "
            f"{bad_channel} (allowed: {sorted(_VALID_REACH_CHANNELS)})"
        )

    _check_pct_columns_bounded(reach, _REACH_PCT_COLUMNS, "media_reachability_by_segment", errors)

    if "segment_size" in reach.columns and (reach["segment_size"] <= 0).any():
        errors.append("media_reachability_by_segment: segment_size must be > 0")


def _check_reach_dept_identity_keys(reach_dept: pd.DataFrame, errors: list[str]) -> bool:
    from population_segmentation.data.segment_reachability_aggregate import (
        DEPARTMENTS as _DEPARTMENTS,
    )
    from population_segmentation.data.segment_reachability_aggregate import (
        SEGMENT_LABELS as _SEGMENT_LABELS,
    )

    expected_rows = len(_SEGMENT_LABELS) * len(_DEPARTMENTS)
    if len(reach_dept) != expected_rows:
        errors.append(
            "media_reachability_by_segment_department: expected "
            f"{expected_rows} rows ((segment, department) cartesian), "
            f"got {len(reach_dept)}"
        )

    if reach_dept.duplicated(["segment_label", "department"]).any():
        n_dup = int(reach_dept.duplicated(["segment_label", "department"]).sum())
        errors.append(
            "media_reachability_by_segment_department: "
            f"{n_dup} duplicate (segment_label, department) rows"
        )

    bad_seg = set(reach_dept["segment_label"].unique()) - set(_SEGMENT_LABELS)
    if bad_seg:
        errors.append(
            "media_reachability_by_segment_department: "
            f"non-canonical segment_label values: {bad_seg}"
        )

    bad_dept = set(reach_dept["department"].unique()) - set(_DEPARTMENTS)
    if bad_dept:
        errors.append(
            "media_reachability_by_segment_department: "
            f"non-canonical department values: {bad_dept}"
        )

    bad_region = set(reach_dept["region"].unique()) - _VALID_REGIONS
    if bad_region:
        errors.append(
            "media_reachability_by_segment_department: " f"invalid region values: {bad_region}"
        )
    return True


def _check_reach_dept_numeric_columns(reach_dept: pd.DataFrame, errors: list[str]) -> None:
    if (reach_dept["segment_size"] < 0).any():
        errors.append("media_reachability_by_segment_department: segment_size must be >= 0")

    _check_pct_columns_bounded(
        reach_dept,
        ("segment_size_pct_of_department", "segment_size_pct_of_segment"),
        "media_reachability_by_segment_department",
        errors,
    )

    mean_cols = (
        "mean_participation_propensity",
        "pct_internet_access",
        "mean_tv_penetration",
        "mean_radio_penetration",
        "mean_whatsapp_penetration",
        "pct_rural",
        "pct_jopara",
    )
    for col in mean_cols:
        if col not in reach_dept.columns:
            continue
        valid = reach_dept[col].dropna()
        if not bool(valid.between(0.0, 1.0).all()):
            n_bad = int((~valid.between(0.0, 1.0)).sum())
            errors.append(
                f"media_reachability_by_segment_department: {col} has "
                f"{n_bad} non-null values outside [0, 1]"
            )

    if "primary_reach_channel" not in reach_dept.columns:
        return
    non_null = reach_dept["primary_reach_channel"].dropna()
    bad_channel = set(non_null.unique()) - _VALID_REACH_CHANNELS
    if bad_channel:
        errors.append(
            "media_reachability_by_segment_department: "
            f"invalid primary_reach_channel values: {bad_channel}"
        )


def _validate_media_reachability_dept(reach_dept: pd.DataFrame, errors: list[str]) -> None:
    missing_cols = [c for c in _MEDIA_DEPT_REQUIRED_COLUMNS if c not in reach_dept.columns]
    if missing_cols:
        errors.append(
            "media_reachability_by_segment_department missing columns: " f"{missing_cols}"
        )
        return

    _check_reach_dept_identity_keys(reach_dept, errors)
    _check_reach_dept_numeric_columns(reach_dept, errors)


_SEGMENT_LABELS_COLUMNS: tuple[str, ...] = (
    "entity_id",
    "segment_label",
    "segment_id",
    "dbscan_noise_flag",
)


def _gate_shared_core_contracts(
    master: pd.DataFrame,
    prop: pd.DataFrame,
    labels: pd.DataFrame,
    reach: pd.DataFrame,
    reach_dept: pd.DataFrame,
) -> None:
    """Route the written Module A artifacts through the shared contract core.

    Enforces every constraint key each artifact's ``schema_contracts/*.yaml``
    declares (nullable, allowed_values, min/max, pattern, per-field unique,
    unique_key, row_count) so Module A's exports pass through the same gate as
    every other module's producers. Operates on the exact frames written to
    disk; the bespoke :func:`_validate_export_contracts` checks run first.

    Raises:
        ValueError: If any written frame violates its declared contract.
    """
    written: list[tuple[pd.DataFrame, str]] = [
        (master, "population_master_clean"),
        (prop, "participation_propensity"),
        (cast(pd.DataFrame, labels[list(_SEGMENT_LABELS_COLUMNS)]), "segment_labels"),
        (reach, "media_reachability_by_segment"),
        (reach_dept, "media_reachability_by_segment_department"),
    ]
    errors: list[str] = []
    for frame, schema_name in written:
        contract = load_named_contract(_SCHEMA_CONTRACTS_DIR, schema_name)
        errors.extend(check_frame(frame, contract))
    if errors:
        msg = "\n".join(f"  • {e}" for e in errors)
        raise ValueError(f"[export] shared contract core validation FAILED:\n{msg}")


def _validate_export_contracts(
    master: pd.DataFrame,
    prop: pd.DataFrame,
    labels: pd.DataFrame,
    anchors: dict[str, Any],
    reach: pd.DataFrame | None = None,
    reach_dept: pd.DataFrame | None = None,
) -> None:
    """Raise ValueError if any hard contract constraint is violated.

    Checks run on the in-memory DataFrames before callers read parquet files,
    giving immediate feedback and a clear error message.

    Parameters
    ----------
    master:
        ``population_master_clean`` frame.
    prop:
        ``participation_propensity`` frame.
    labels:
        ``segment_labels`` frame.
    anchors:
        Calibration anchors dict.
    reach:
        ``media_reachability_by_segment`` frame (optional; validated when provided).
    """
    errors: list[str] = []

    _check_duplicate_entity_ids(master, "population_master_clean", errors)
    _check_duplicate_entity_ids(prop, "participation_propensity", errors)
    _check_duplicate_entity_ids(labels, "segment_labels", errors)
    _check_row_count_alignment(master, prop, labels, errors)
    _check_propensity_range(prop, errors)
    _check_department_calibration(master, prop, anchors, errors)

    from population_segmentation.models.segmentation import SEGMENT_LABEL_MAP

    valid_labels = set(SEGMENT_LABEL_MAP.values())
    bad_seg = set(labels["segment_label"].unique()) - valid_labels
    if bad_seg:
        errors.append(f"segment_labels contains non-canonical labels: {bad_seg}")

    if reach is not None:
        _validate_media_reachability(reach, valid_labels, errors)
    if reach_dept is not None:
        _validate_media_reachability_dept(reach_dept, errors)

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
    """CLI entry for ``python -m population_segmentation.pipeline.export``.

    Parses paths, loads YAML config and anchors, runs :func:`run_export`, and
    prints artifact paths to stdout.

    Args:
        argv: Optional argument vector (defaults to ``sys.argv[1:]`` when invoked
            as ``__main__``).

    Returns:
        None

    Raises:
        SystemExit: Propagated from :func:`argparse.ArgumentParser.parse_args` on
            invalid CLI usage.

    Example:
        From the repository root after ``poetry install``::

            python -m population_segmentation.pipeline.export --config ... \\
                --anchors ... --out-dir ...
    """
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

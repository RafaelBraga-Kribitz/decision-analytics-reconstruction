#!/usr/bin/env python3
"""Export Module A portfolio charts to reports/module_a/.

Writes:
  - reliability_diagram.png — training-target reference diagnostic (matplotlib)
  - shap_summary.png — mean |SHAP| bar chart from pipeline propensity model

Requires processed Module A artifacts (``make module-a-pipeline``).
SHAP requires ``poetry install --extras explainability``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "module_a"
DATA = ROOT / "data" / "processed"
ANCHORS = ROOT / "module_a_population_segmentation" / "config" / "calibration_anchors.yaml"
MODEL_PARAMS = ROOT / "module_a_population_segmentation" / "config" / "model_params.yaml"

RELIABILITY_DISCLAIMER = (
    "Synthetic training labels (dept/youth/gender anchors) — not held-out calibration"
)


def write_reliability_diagram(out_path: Path) -> None:
    from population_segmentation.models.propensity import synthetic_training_reference_labels
    from population_segmentation.visualization.calibration_curves import reliability_frame

    pop = pd.read_parquet(DATA / "population_master_clean.parquet")
    with open(ANCHORS, encoding="utf-8") as f:
        anc = yaml.safe_load(f)
    y_true = synthetic_training_reference_labels(pop, anc, random_state=42)
    y_prob = pop["participation_propensity"].to_numpy()
    frame = reliability_frame(y_true, y_prob)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(frame["predicted_mean"], frame["observed_mean"], "o-", label="Model", color="#e60000")
    ax.plot([0, 1], [0, 1], "--", color="#25282b", label="Perfect calibration")
    ax.set_xlabel("Predicted mean propensity (bin)")
    ax.set_ylabel("Observed rate (training-target labels)")
    ax.set_title("Reliability diagram — training-target reference diagnostic")
    ax.legend(fontsize=9, loc="upper left")
    fig.text(0.5, 0.01, RELIABILITY_DISCLAIMER, ha="center", fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def write_shap_summary(out_path: Path) -> int:
    try:
        import shap
        from population_segmentation.features.behavioral import build_behavioral_features
        from population_segmentation.features.demographic import build_demographic_features
        from population_segmentation.features.reachability import build_reachability_features
        from population_segmentation.models.propensity import PropensityModel
    except ImportError:
        return 2

    pop = pd.read_parquet(DATA / "population_master_clean.parquet")
    with open(ANCHORS, encoding="utf-8") as f:
        anc = yaml.safe_load(f)
    with open(MODEL_PARAMS, encoding="utf-8") as f:
        mp = yaml.safe_load(f)
    stratify = tuple(mp["propensity"]["stratify_by"])

    feat = build_reachability_features(build_behavioral_features(build_demographic_features(pop)))
    seg_path = DATA / "segment_labels.parquet"
    if "segment_label" not in feat.columns and seg_path.is_file():
        segs = pd.read_parquet(seg_path)
        feat = feat.merge(segs[["entity_id", "segment_label"]], on="entity_id", how="left")

    prop = PropensityModel(random_state=42, stratify_by=stratify).fit_predict(feat, anc)
    x_scaled = prop["x_all_scaled"][:2000]
    feature_names = prop["feature_names"]
    explainer = shap.LinearExplainer(prop["fitted_model"], x_scaled, feature_names=feature_names)
    shap_values = explainer.shap_values(x_scaled)
    shap_vals = shap_values[1] if isinstance(shap_values, list) else shap_values

    shap.summary_plot(
        shap_vals,
        x_scaled,
        feature_names=feature_names,
        plot_type="bar",
        show=False,
    )
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    return 0


def main() -> int:
    pop_path = DATA / "population_master_clean.parquet"
    if not pop_path.is_file():
        print(f"Missing {pop_path} — run make module-a-pipeline first", file=sys.stderr)
        return 1

    rel_path = OUT / "reliability_diagram.png"
    write_reliability_diagram(rel_path)
    print(f"wrote {rel_path}")

    shap_path = OUT / "shap_summary.png"
    rc = write_shap_summary(shap_path)
    if rc == 2:
        print(
            "SHAP extra not installed — reliability_diagram.png written; "
            "run poetry install --extras explainability for shap_summary.png",
            file=sys.stderr,
        )
        return 1

    print(f"wrote {shap_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

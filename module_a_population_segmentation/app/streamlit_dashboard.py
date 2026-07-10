"""Module A Streamlit dashboard (four tabs: segments, propensity, QA, SHAP)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import yaml
from population_segmentation.data.cleaner import clean_population
from population_segmentation.data.generator import generate_population
from population_segmentation.data.raw_injector import inject_flaws
from population_segmentation.features.behavioral import build_behavioral_features
from population_segmentation.features.demographic import build_demographic_features
from population_segmentation.features.reachability import build_reachability_features
from population_segmentation.models.propensity import PropensityModel
from population_segmentation.models.segmentation import build_segmentation_frame
from population_segmentation.visualization.calibration_curves import (
    reliability_chart,
    reliability_frame,
)
from population_segmentation.visualization.segment_profiles import (
    segment_profile_table,
    segment_size_chart,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _processed_dir() -> Path:
    return _repo_root() / "data" / "processed"


def _load_cfg() -> tuple[dict, dict, tuple[str, ...]]:
    mod = _repo_root() / "module_a_population_segmentation" / "config"
    with open(mod / "generation.yaml") as f:
        gen = yaml.safe_load(f)
    with open(mod / "calibration_anchors.yaml") as f:
        anc = yaml.safe_load(f)
    with open(mod / "model_params.yaml") as f:
        mp = yaml.safe_load(f)
    strat = tuple(mp["propensity"]["stratify_by"])
    return gen, anc, strat


@st.cache_data(show_spinner=False)
def _load_canonical_bundle() -> tuple[pd.DataFrame, dict[str, float], dict[str, Any], dict, str]:
    """Load the canonical Module A export bundle from data/processed/."""
    processed = _processed_dir()
    master_path = processed / "population_master_clean.parquet"
    manifest_path = processed / "model_run_manifest.json"

    if not master_path.is_file():
        raise FileNotFoundError(
            f"Missing canonical export at {master_path}. "
            "Run `poetry run python -m population_segmentation.pipeline.export` first."
        )

    feat = pd.read_parquet(master_path)
    prop_path = processed / "participation_propensity.parquet"
    if prop_path.is_file() and "participation_propensity" not in feat.columns:
        prop_df = pd.read_parquet(prop_path)
        feat = feat.merge(prop_df[["entity_id", "participation_propensity"]], on="entity_id")

    run_id = "unknown"
    seg_metrics: dict[str, float] = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        commit = str(manifest.get("git_commit", "unknown"))
        run_id = commit[:12]
        raw_seg = manifest.get("segmentation_metrics") or {}
        if isinstance(raw_seg, dict):
            seg_metrics = {k: float(v) for k, v in raw_seg.items()}

    _, anc, stratify_by = _load_cfg()
    prop = PropensityModel(random_state=42, stratify_by=stratify_by).fit_predict(feat, anc)
    return feat, seg_metrics, prop, anc, run_id


@st.cache_data(show_spinner=False)
def _build_sample(sample_size: int = 15000):
    """Non-canonical live rebuild (developer override only)."""
    gen, anc, stratify_by = _load_cfg()
    gen["sample_size"] = sample_size
    base = generate_population(gen, seed=42)
    raw = inject_flaws(base, gen, seed=42)
    clean = clean_population(
        raw,
        gen,
        qa_report_dir=_repo_root() / "module_a_population_segmentation" / "reports",
    )
    feat = build_reachability_features(build_behavioral_features(build_demographic_features(clean)))
    labels_df, seg = build_segmentation_frame(feat, k=6, random_state=42)
    feat = feat.copy()
    feat = feat.reset_index(drop=True)
    feat["segment_label"] = labels_df["segment_label"].to_numpy()
    feat["segment_id"] = labels_df["segment_id"].to_numpy()
    feat["dbscan_noise_flag"] = labels_df["dbscan_noise_flag"].to_numpy()
    prop = PropensityModel(random_state=42, stratify_by=stratify_by).fit_predict(feat, anc)
    feat["participation_propensity"] = prop["predictions"].values
    return raw, feat, seg, prop, anc


def _make_national_reference_labels(n: int, national_rate: float, seed: int = 42) -> np.ndarray:
    """Generate Bernoulli labels at the national participation rate.

    This is a *national-rate reference* used only for the reliability
    diagnostic chart.  It is NOT the model's training target (which
    incorporates department, youth, and gender deviations).
    """
    return (np.random.default_rng(seed).random(n) < national_rate).astype(int)


def _render_shap_summary(model: Any, x_scaled: np.ndarray, feature_names: list[str]) -> None:
    """Render the SHAP mean-|SHAP| bar summary with explicit figure ownership.

    ``shap.summary_plot(show=False)`` returns ``None`` on the pinned shap
    version (verified), so the figure it drew is captured explicitly with no
    ambient state from other tabs — ``None`` can never reach ``st.pyplot``
    and two renders of the same inputs are identical (IMP-V06 / issue #70).
    """
    import shap

    with st.spinner("Computing SHAP values..."):
        explainer = shap.LinearExplainer(model, x_scaled, feature_names=feature_names)
        shap_values = explainer.shap_values(x_scaled)
        shap_vals = shap_values[1] if isinstance(shap_values, list) else shap_values

    plt.close("all")
    shap.summary_plot(shap_vals, x_scaled, feature_names=feature_names, plot_type="bar", show=False)
    fig_shap = plt.gcf()
    if not fig_shap.axes:
        raise RuntimeError("shap.summary_plot drew no axes — cannot render SHAP tab")
    st.pyplot(fig_shap, use_container_width=True)
    plt.close(fig_shap)
    st.write(
        "**Interpretation:** Features ordered by mean |SHAP value|. "
        "Higher = more important for model predictions."
    )


def main() -> None:
    st.set_page_config(page_title="Module A Dashboard", layout="wide")
    st.title("Module A — Population Modeling and Segmentation")

    use_live_rebuild = st.sidebar.checkbox(
        "Live rebuild (non-canonical)",
        value=False,
        help="When unchecked, loads data/processed/population_master_clean.parquet "
        "from the last export run (same bundle as committed charts).",
    )

    if use_live_rebuild:
        sample_size = st.sidebar.slider(
            "Sample size", min_value=5000, max_value=30000, value=15000, step=1000
        )
        raw, feat, seg, prop, anc = _build_sample(sample_size)
        run_id = f"live-{sample_size}"
    else:
        feat, seg, prop, anc, run_id = _load_canonical_bundle()
        st.sidebar.caption(f"Canonical run `{run_id}` · N={len(feat):,}")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Segment Explorer", "Propensity Calibration", "Data Quality Report", "SHAP Importance"]
    )

    with tab1:
        st.subheader("Segment Explorer")
        if "silhouette" in seg:
            st.metric("Silhouette (k=6)", f"{seg['silhouette']:.3f}")
        if "bootstrap_ari" in seg:
            st.metric("Bootstrap ARI", f"{seg['bootstrap_ari']:.3f}")
        prof = segment_profile_table(feat)
        st.dataframe(prof, use_container_width=True)
        st.plotly_chart(segment_size_chart(prof), use_container_width=True)

    with tab2:
        st.subheader("Propensity — National-Rate Reference Diagnostic")
        st.caption(
            "**Note:** the reliability chart below compares raked propensity scores against "
            "Bernoulli labels drawn at the *national* participation rate.  This is a "
            "national-rate reference baseline, not the model's training target (which "
            "incorporates department, youth, and gender deviations).  It indicates "
            "aggregate-level alignment, not held-out predictive calibration."
        )
        y_true = _make_national_reference_labels(
            len(feat), float(anc["national"]["participation_rate"]), seed=42
        )
        y_prob = feat["participation_propensity"].to_numpy()
        rel = reliability_frame(y_true, y_prob)
        # Shared IMP-V04 builder returns a matplotlib Figure (square axes,
        # Wilson intervals, in-canvas disclaimer) — rendered via st.pyplot.
        st.pyplot(
            reliability_chart(rel, subtitle="national-rate reference diagnostic"),
            use_container_width=True,
        )
        st.write("Calibration summary (post-rake department means vs TSJE anchors)")
        st.json(prop["calibration"])

    with tab3:
        st.subheader("Data Quality Report")
        # The cleaning pipeline emits qa_report_<YYYYMMDD>.md (a fresh date each
        # run). Glob for the most recent one instead of a hard-coded date so the
        # tab populates regardless of when the pipeline last ran (AUD-PUB-001).
        reports_dir = Path(__file__).resolve().parents[1] / "reports"
        qa_reports = sorted(reports_dir.glob("qa_report_*.md"))
        if qa_reports:
            qa_path = qa_reports[-1]
            st.caption(f"Showing latest QA report: {qa_path.name}")
            st.markdown(qa_path.read_text(encoding="utf-8"))
        else:
            st.info("QA report not found yet. Run cleaning pipeline first.")
        st.write(f"Rows loaded: {len(feat)}")
        default_path = "data/processed/population_master_clean.parquet"
        source = "live rebuild" if use_live_rebuild else default_path
        st.write(f"Data source: {source}")

    with tab4:
        st.subheader("SHAP Feature Importance — Propensity Model")
        st.caption(
            "Feature importance for the underlying logistic regression (before raking). "
            "SHAP explains model predictions via Shapley values."
        )

        try:
            import shap
        except ImportError:
            st.warning(
                "SHAP is not installed. Run `poetry install --extras explainability` "
                "to enable this tab. The other tabs work without it."
            )
            st.stop()

        model = prop["fitted_model"]
        feature_names = prop["feature_names"]
        x_scaled = prop["x_all_scaled"]

        col1, col2 = st.columns(2)
        with col1:
            importance_type = st.radio(
                "Importance metric", ["Summary (mean |SHAP|)", "Individual entity force plot"]
            )

        if importance_type == "Summary (mean |SHAP|)":
            _render_shap_summary(model, x_scaled, feature_names)

        else:
            entity_idx = st.slider("Select entity", 0, len(feat) - 1, 0)
            with st.spinner("Computing SHAP values..."):
                explainer = shap.LinearExplainer(model, x_scaled, feature_names=feature_names)
                shap_values = explainer.shap_values(x_scaled[[entity_idx]])
                shap_vals = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]

            entity_id = feat.index[entity_idx]
            pred_prob = feat.iloc[entity_idx]["participation_propensity"]

            st.write(f"**Entity ID:** {entity_id}")
            st.write(f"**Predicted participation propensity:** {pred_prob:.3f}")

            shap_df = pd.DataFrame(
                {"Feature": feature_names, "SHAP value": shap_vals, "|SHAP|": np.abs(shap_vals)}
            ).sort_values("|SHAP|", ascending=True)

            st.bar_chart(shap_df.set_index("Feature")["SHAP value"])
            st.write(
                "Red (positive) = increases propensity." " Blue (negative) = decreases propensity."
            )


if __name__ == "__main__":
    main()

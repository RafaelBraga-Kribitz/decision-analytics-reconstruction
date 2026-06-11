"""Module A Streamlit dashboard (four tabs: segments, propensity, QA, SHAP)."""

from __future__ import annotations

from pathlib import Path

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


def _load_cfg() -> tuple[dict, dict, tuple[str, ...]]:
    root = Path(__file__).resolve().parents[2]
    mod = root / "module_a_population_segmentation" / "config"
    with open(mod / "generation.yaml") as f:
        gen = yaml.safe_load(f)
    with open(mod / "calibration_anchors.yaml") as f:
        anc = yaml.safe_load(f)
    with open(mod / "model_params.yaml") as f:
        mp = yaml.safe_load(f)
    strat = tuple(mp["propensity"]["stratify_by"])
    return gen, anc, strat


@st.cache_data(show_spinner=False)
def _build_sample(sample_size: int = 15000):
    gen, anc, stratify_by = _load_cfg()
    gen["sample_size"] = sample_size
    base = generate_population(gen, seed=42)
    raw = inject_flaws(base, gen, seed=42)
    clean = clean_population(
        raw,
        gen,
        qa_report_dir=Path(__file__).resolve().parents[2]
        / "module_a_population_segmentation"
        / "reports",
    )
    feat = build_reachability_features(build_behavioral_features(build_demographic_features(clean)))
    labels_df, seg = build_segmentation_frame(feat, k=6, random_state=42)
    feat = feat.copy()
    feat = feat.reset_index(drop=True)
    # Mirror the export pipeline: attach all segment columns so dashboard output
    # columns match what downstream consumers (Module B/C) receive from run_export().
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
    incorporates department, youth, and gender deviations).  The chart
    therefore shows how well the model's raked propensity scores track a
    simple national-rate baseline, not the learned synthetic labels.

    Parameters
    ----------
    n:
        Number of labels to generate.
    national_rate:
        Target Bernoulli success probability (national participation rate).
    seed:
        RNG seed for reproducibility.

    Returns
    -------
    np.ndarray of int (0/1), shape (n,).
    """
    return (np.random.default_rng(seed).random(n) < national_rate).astype(int)


def main() -> None:
    st.set_page_config(page_title="Module A Dashboard", layout="wide")
    st.title("Module A — Population Modeling and Segmentation")

    sample_size = st.sidebar.slider(
        "Sample size", min_value=5000, max_value=30000, value=15000, step=1000
    )
    raw, feat, seg, prop, anc = _build_sample(sample_size)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Segment Explorer", "Propensity Calibration", "Data Quality Report", "SHAP Importance"]
    )

    with tab1:
        st.subheader("Segment Explorer")
        st.metric("Silhouette (k=6)", f"{seg['silhouette']:.3f}")
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
        st.plotly_chart(reliability_chart(rel), use_container_width=True)
        st.write("Calibration summary (post-rake department means vs TSJE anchors)")
        st.json(prop["calibration"])

    with tab3:
        st.subheader("Data Quality Report")
        qa_path = Path(__file__).resolve().parents[1] / "reports" / "qa_report_20260507.md"
        if qa_path.exists():
            st.markdown(qa_path.read_text(encoding="utf-8"))
        else:
            st.info("QA report not found yet. Run cleaning pipeline first.")
        st.write(f"Raw rows: {len(raw)}")
        st.write(f"Clean rows: {len(feat)}")

    with tab4:
        st.subheader("SHAP Feature Importance — Propensity Model")
        st.caption(
            "Feature importance for the underlying logistic regression (before raking). "
            "SHAP explains model predictions via Shapley values."
        )

        # Lazy import: shap is an optional extra. The dashboard must start
        # without it; only this tab requires it.
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
            with st.spinner("Computing SHAP values..."):
                explainer = shap.LinearExplainer(model, x_scaled, feature_names=feature_names)
                shap_values = explainer.shap_values(x_scaled)
                shap_vals = shap_values[1] if isinstance(shap_values, list) else shap_values

            fig = shap.summary_plot(
                shap_vals, x_scaled, feature_names=feature_names, plot_type="bar", show=False
            )
            st.pyplot(fig, use_container_width=True)
            st.write(
                "**Interpretation:** Features ordered by mean |SHAP value|. "
                "Higher = more important for model predictions."
            )

        else:  # Individual force plot
            entity_idx = st.slider("Select entity", 0, len(feat) - 1, 0)
            with st.spinner("Computing SHAP values..."):
                explainer = shap.LinearExplainer(model, x_scaled, feature_names=feature_names)
                shap_values = explainer.shap_values(x_scaled[[entity_idx]])
                shap_vals = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]

            entity_id = feat.index[entity_idx]
            pred_prob = feat.iloc[entity_idx]["participation_propensity"]

            st.write(f"**Entity ID:** {entity_id}")
            st.write(f"**Predicted participation propensity:** {pred_prob:.3f}")

            # Force plot (bar chart approximation for Streamlit)
            shap_df = pd.DataFrame(
                {"Feature": feature_names, "SHAP value": shap_vals, "|SHAP|": np.abs(shap_vals)}
            ).sort_values("|SHAP|", ascending=True)

            st.bar_chart(shap_df.set_index("Feature")["SHAP value"])
            st.write(
                "Red (positive) = increases propensity." " Blue (negative) = decreases propensity."
            )


if __name__ == "__main__":
    main()

"""Module A Streamlit dashboard (three tabs)."""

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
from population_segmentation.models.segmentation import KMeansSegmenter
from population_segmentation.visualization.calibration_curves import (
    reliability_chart,
    reliability_frame,
)
from population_segmentation.visualization.segment_profiles import (
    segment_profile_table,
    segment_size_chart,
)


def _load_cfg() -> tuple[dict, dict]:
    root = Path(__file__).resolve().parents[2]
    with open(root / "module_a_population_segmentation" / "config" / "generation.yaml") as f:
        gen = yaml.safe_load(f)
    with open(
        root / "module_a_population_segmentation" / "config" / "calibration_anchors.yaml"
    ) as f:
        anc = yaml.safe_load(f)
    return gen, anc


@st.cache_data(show_spinner=False)
def _build_sample(sample_size: int = 15000):
    gen, anc = _load_cfg()
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
    seg = KMeansSegmenter(k=6, random_state=42).fit_predict(feat)
    feat = feat.copy()
    feat["segment_label"] = (
        pd.Series(seg["labels"])
        .map(
            {
                0: "rural_committed",
                1: "urban_high_volatility",
                2: "youth_volatile",
                3: "structurally_dependent_bloc",
                4: "rural_low_propensity",
                5: "committed_opposition",
            }
        )
        .fillna("urban_high_volatility")
    )
    prop = PropensityModel(random_state=42).fit_predict(feat, anc)
    feat["participation_propensity"] = prop["predictions"].values
    return raw, feat, seg, prop, anc


def main() -> None:
    st.set_page_config(page_title="Module A Dashboard", layout="wide")
    st.title("Module A — Population Modeling and Segmentation")

    sample_size = st.sidebar.slider(
        "Sample size", min_value=5000, max_value=30000, value=15000, step=1000
    )
    raw, feat, seg, prop, anc = _build_sample(sample_size)

    tab1, tab2, tab3 = st.tabs(
        ["Segment Explorer", "Propensity Calibration", "Data Quality Report"]
    )

    with tab1:
        st.subheader("Segment Explorer")
        st.metric("Silhouette (k=6)", f"{seg['silhouette']:.3f}")
        st.metric("Bootstrap ARI", f"{seg['bootstrap_ari']:.3f}")
        prof = segment_profile_table(feat)
        st.dataframe(prof, use_container_width=True)
        st.plotly_chart(segment_size_chart(prof), use_container_width=True)

    with tab2:
        st.subheader("Propensity Calibration")
        rng = np.random.default_rng(42)
        y_true = (rng.random(len(feat)) < anc["national"]["participation_rate"]).astype(int)
        y_prob = feat["participation_propensity"].to_numpy()
        rel = reliability_frame(y_true, y_prob)
        st.plotly_chart(reliability_chart(rel), use_container_width=True)
        st.write("Calibration summary")
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


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Verification script for F-088 (Module A config-runtime and doc parity).

(a) Every key in the pca/dbscan/kmeans/propensity sections of model_params.yaml
    is either a fit-time hyperparameter the code loads (and the model defaults
    equal it) or a named acceptance gate; nothing is decorative.
(b) The configured bootstrap count is the count that executes.
(c) segmentation_features equals the code's FEATURE_COLUMNS.
(d) Gate numbers quoted in the Module A README and model cards equal the YAML.
(e) Every relative link in the Module A README resolves; no "14-step" claim.

Spec: governance/improvement_plan/IMP-A06_config-doc-parity.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest import mock

import numpy as np
import yaml
from _governance_check import REPO_ROOT, gate

MODULE_A = REPO_ROOT / "module_a_population_segmentation"
README = MODULE_A / "README.md"
CARD_SEG = MODULE_A / "reports" / "model_card_segmentation.md"
CARD_PROP = MODULE_A / "reports" / "model_card_propensity.md"

GATE_KEYS = {
    "dbscan": {"max_noise_rate"},
    "kmeans": {"silhouette_threshold", "bootstrap_ari_threshold"},
    "propensity": {
        "brier_threshold",
        "auc_floor",
        "auc_floor_ablated",
        "reliability_max_deviation_pp",
    },
}


def _config_gaps() -> list[str]:
    from population_segmentation.utils.model_params import effective_hyperparameters, section

    effective = effective_hyperparameters()
    gaps = []
    for name, consumed in effective.items():
        unknown = set(section(name)) - set(consumed) - GATE_KEYS.get(name, set())
        gaps += [f"model_params.{name}.{k} has no runtime consumer" for k in sorted(unknown)]
    return gaps


def _runtime_gaps() -> list[str]:
    from population_segmentation.pipeline.models import segmentation as seg
    from population_segmentation.pipeline.models.propensity import PropensityModel
    from population_segmentation.utils.model_params import section

    km, db, prop = section("kmeans"), section("dbscan"), section("propensity")
    s, f = seg.KMeansSegmenter(), seg.DBSCANNoiseFilter()
    expected = {
        "kmeans": (s.k, s.n_init, s.init, s.max_iter, s.bootstrap_n_samples),
        "kmeans_yaml": (
            km["default_k"],
            km["n_init"],
            km["init"],
            km["max_iter"],
            km["bootstrap_n_samples"],
        ),
    }
    gaps = []
    if expected["kmeans"] != expected["kmeans_yaml"]:
        gaps.append(
            f"KMeansSegmenter defaults {expected['kmeans']} != yaml {expected['kmeans_yaml']}"
        )
    if (f.eps, f.min_samples, f.metric) != (db["eps"], db["min_samples"], db["metric"]):
        gaps.append("DBSCANNoiseFilter defaults differ from model_params.dbscan")
    if PropensityModel().random_state != prop["random_state"]:
        gaps.append("PropensityModel.random_state differs from model_params.propensity")
    with mock.patch.object(seg, "compute_bootstrap_ari", return_value=0.5) as ari:
        x = np.random.default_rng(0).normal(size=(60, 3))
        s._bootstrap_ari(x, np.zeros(60, dtype=int))
    if ari.call_args.kwargs.get("n_bootstrap") != km["bootstrap_n_samples"]:
        gaps.append("configured bootstrap_n_samples is not the executed count")
    if list(seg.FEATURE_COLUMNS) != list(seg._MODEL_PARAMS.get("segmentation_features", [])):
        gaps.append("segmentation_features differs from FEATURE_COLUMNS")
    return gaps


def _doc_gaps() -> list[str]:
    params = yaml.safe_load((MODULE_A / "config" / "model_params.yaml").read_text(encoding="utf-8"))
    km, prop = params["kmeans"], params["propensity"]
    readme = README.read_text(encoding="utf-8")
    cards = CARD_SEG.read_text(encoding="utf-8") + CARD_PROP.read_text(encoding="utf-8")
    quoted = {
        f"silhouette > {km['silhouette_threshold']}": readme,
        f"bootstrap ARI ≥ {km['bootstrap_ari_threshold']:.2f}": readme,
        f"ablated AUC-ROC > {prop['auc_floor_ablated']}": readme,
        f"Brier < {prop['brier_threshold']}": readme,
        f"reliability deviation < {prop['reliability_max_deviation_pp']:g} pp": readme,
        f"Silhouette > {km['silhouette_threshold']}": cards,
        f"Brier score < {prop['brier_threshold']}": cards,
    }
    gaps = [
        f"doc gate {k!r} does not match model_params.yaml" for k, t in quoted.items() if k not in t
    ]
    for target in re.findall(r"\]\(([^)#]+)\)", readme):
        if not target.startswith("http") and not (README.parent / target).exists():
            gaps.append(f"Module A README links missing file {target}")
    if "14-step" in readme:
        gaps.append('Module A README repeats the unverifiable "14-step" claim')
    return gaps


def main() -> int:
    sys.path.insert(0, str(MODULE_A / "src"))
    try:
        gaps = _config_gaps() + _runtime_gaps()
    except (ImportError, AttributeError, KeyError) as exc:
        gaps = [f"config wiring missing ({exc!r})"]
    gaps += _doc_gaps()
    return gate("F-088", Path(__file__).name, not gaps, "; ".join(gaps))


if __name__ == "__main__":
    sys.exit(main())

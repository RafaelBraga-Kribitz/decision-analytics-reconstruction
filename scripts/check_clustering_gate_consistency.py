#!/usr/bin/env python3
"""Verification script for F-089 (clustering gate and metric integrity).

(a) The 50k production run (data/processed/model_run_manifest.json, which the
    Adversary job regenerates) clears the YAML gates: silhouette > threshold,
    bootstrap ARI >= threshold, DBSCAN noise <= max_noise_rate. Before this
    finding no check asserted the production numbers at all.
(b) The gate numbers agree across model_params.yaml, the segmentation model
    card and reports/NUMERIC_SSOT.md, and the 15k ARI test floor the YAML
    documents is the one tests/test_segmentation.py asserts.
(c) Exactly one bootstrap-ARI implementation exists in src, and the
    segmenter delegates to it.
(d) Davies-Bouldin, Calinski-Harabasz and PSI have production callers.

Spec: governance/improvement_plan/IMP-A03_cluster-selection-gates.md
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml
from _governance_check import REPO_ROOT, gate

MODULE_A = REPO_ROOT / "module_a_population_segmentation"
SRC = MODULE_A / "src" / "population_segmentation"
PARAMS = MODULE_A / "config" / "model_params.yaml"
CARD = MODULE_A / "reports" / "model_card_segmentation.md"
SSOT = REPO_ROOT / "reports" / "NUMERIC_SSOT.md"
SEG_TEST = MODULE_A / "tests" / "test_segmentation.py"
MANIFEST = REPO_ROOT / "data" / "processed" / "model_run_manifest.json"
PRODUCTION_CALLERS = {
    "compute_davies_bouldin": SRC / "pipeline" / "models" / "segmentation.py",
    "compute_calinski_harabasz": SRC / "pipeline" / "models" / "segmentation.py",
    "population_stability_index": SRC / "pipeline" / "export.py",
}


def _production_gaps(params: dict) -> list[str]:
    if not MANIFEST.is_file():
        return ["missing data/processed/model_run_manifest.json (run the 50k pipeline)"]
    m = json.loads(MANIFEST.read_text(encoding="utf-8")).get("segmentation_metrics", {})
    km, db = params["kmeans"], params["dbscan"]
    checks = {
        f"silhouette {m.get('silhouette')} > {km['silhouette_threshold']}": m.get("silhouette", 0)
        > km["silhouette_threshold"],
        f"bootstrap_ari {m.get('bootstrap_ari')} >= {km['bootstrap_ari_threshold']}": m.get(
            "bootstrap_ari", 0
        )
        >= km["bootstrap_ari_threshold"],
        f"noise_rate {m.get('noise_rate')} <= {db['max_noise_rate']}": m.get("noise_rate", 1)
        <= db["max_noise_rate"],
    }
    return [f"50k production run fails gate: {name}" for name, ok in checks.items() if not ok]


def _surface_gaps(params: dict) -> list[str]:
    km = params["kmeans"]
    sil, ari = km["silhouette_threshold"], km["bootstrap_ari_threshold"]
    card, ssot = CARD.read_text(encoding="utf-8"), SSOT.read_text(encoding="utf-8")
    expected = {
        "model card silhouette gate": (f"Silhouette > {sil}", card),
        "model card ARI gate": (f"Bootstrap ARI ≥ {ari:.2f}", card),
        "NUMERIC_SSOT silhouette gate": (f"**> {sil}**", ssot),
        "NUMERIC_SSOT ARI gate": (f"**≥ {ari:.2f}**", ssot),
    }
    gaps = [f"{name} does not read {s!r}" for name, (s, text) in expected.items() if s not in text]
    documented = re.search(r"15k test floor is ([0-9.]+)", PARAMS.read_text(encoding="utf-8"))
    asserted = re.search(
        r'out\["bootstrap_ari"\] > ([0-9.]+)', SEG_TEST.read_text(encoding="utf-8")
    )
    if not documented or not asserted or documented.group(1).rstrip(".") != asserted.group(1):
        gaps.append("15k bootstrap-ARI test floor in model_params.yaml != test_segmentation.py")
    return gaps


def _implementation_gaps() -> list[str]:
    gaps = []
    ari_impls = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in SRC.rglob("*.py")
        if "adjusted_rand_score(" in p.read_text(encoding="utf-8")
    ]
    if ari_impls != [
        "module_a_population_segmentation/src/population_segmentation/evaluation/clustering_metrics.py"
    ]:
        gaps.append(f"bootstrap ARI must have one implementation, found in {ari_impls}")
    seg = (SRC / "pipeline" / "models" / "segmentation.py").read_text(encoding="utf-8")
    if "compute_bootstrap_ari(" not in seg:
        gaps.append("KMeansSegmenter does not delegate to compute_bootstrap_ari")
    for fn, caller in PRODUCTION_CALLERS.items():
        if f"{fn}(" not in caller.read_text(encoding="utf-8"):
            gaps.append(f"{fn} has no production caller in {caller.name}")
    return gaps


def main() -> int:
    params = yaml.safe_load(PARAMS.read_text(encoding="utf-8"))
    gaps = _production_gaps(params) + _surface_gaps(params) + _implementation_gaps()
    return gate("F-089", Path(__file__).name, not gaps, "; ".join(gaps))


if __name__ == "__main__":
    sys.exit(main())

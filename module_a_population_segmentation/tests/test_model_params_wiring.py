"""model_params.yaml drives the Module A models it describes (F-088 / IMP-A06)."""

from __future__ import annotations

from unittest import mock

import numpy as np
from population_segmentation.pipeline.models import segmentation as seg
from population_segmentation.pipeline.models.propensity import PropensityModel
from population_segmentation.utils.model_params import effective_hyperparameters, section


def test_segmenter_and_filter_defaults_come_from_yaml() -> None:
    km, db = section("kmeans"), section("dbscan")
    s, f = seg.KMeansSegmenter(), seg.DBSCANNoiseFilter()
    assert (s.k, s.n_init, s.init, s.max_iter) == (
        km["default_k"],
        km["n_init"],
        km["init"],
        km["max_iter"],
    )
    assert (s.bootstrap_n_samples, s.bootstrap_subsample_frac) == (
        km["bootstrap_n_samples"],
        km["bootstrap_subsample_frac"],
    )
    assert (f.eps, f.min_samples, f.metric, f.n_jobs) == (
        db["eps"],
        db["min_samples"],
        db["metric"],
        db["n_jobs"],
    )
    assert PropensityModel().random_state == section("propensity")["random_state"]


def test_bootstrap_count_follows_the_segmenter_setting() -> None:
    x = np.random.default_rng(0).normal(size=(60, 3))
    with mock.patch.object(seg, "compute_bootstrap_ari", return_value=0.5) as ari:
        seg.KMeansSegmenter(bootstrap_n_samples=50)._bootstrap_ari(x, np.zeros(60, dtype=int))
    assert ari.call_args.kwargs["n_bootstrap"] == 50


def test_effective_hyperparameters_cover_every_fit_section() -> None:
    eff = effective_hyperparameters()
    assert set(eff) == {"pca", "dbscan", "kmeans", "propensity"}
    assert all(v is not None for block in eff.values() for v in block.values())

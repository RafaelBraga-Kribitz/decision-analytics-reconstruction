"""The exported diagnostics summary the Quarto report reads (F-084)."""

from __future__ import annotations

import arviz as az
import numpy as np
import pytest

from module_c_forecasting_scenarios.models.tracking.hierarchical import (
    DIAGNOSTIC_GATES,
    MODEL_VERSION,
    diagnostics_summary,
)


def _idata(n_div: int, *, mixed: bool) -> az.InferenceData:
    rng = np.random.default_rng(0)
    draws = rng.normal(size=(4, 500))
    if not mixed:
        draws += np.arange(4)[:, None] * 5.0  # chains disagree -> R-hat >> 1.01
    diverging = np.zeros((4, 500), dtype=bool)
    diverging.flat[:n_div] = True
    idata = az.from_dict(
        posterior={"sigma_rw": draws},
        sample_stats={"diverging": diverging},
    )
    idata.attrs["model_version"] = MODEL_VERSION
    return idata


def test_summary_passes_well_mixed_chains(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MC_FAST", raising=False)
    s = diagnostics_summary(_idata(0, mixed=True))
    assert s["model_version"] == MODEL_VERSION
    assert s["sampler_path"] == "full_nuts"
    assert (s["chains"], s["draws"]) == (4, 500)
    assert s["gates"] == DIAGNOSTIC_GATES
    assert all(s["passed"].values()), s
    assert s["values"]["divergences"] == 0


def test_summary_flags_divergences_and_rhat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MC_FAST", "1")
    s = diagnostics_summary(_idata(3, mixed=False))
    assert s["sampler_path"] == "mc_fast"
    assert s["values"]["divergences"] == 3
    assert not s["passed"]["divergences"]
    assert s["values"]["rhat_max"] > DIAGNOSTIC_GATES["rhat_max"]
    assert not s["passed"]["rhat_max"]

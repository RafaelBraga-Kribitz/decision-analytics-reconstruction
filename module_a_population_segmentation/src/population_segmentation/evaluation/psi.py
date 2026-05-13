"""Population Stability Index (PSI) for distribution shift on binned proportions."""

from __future__ import annotations

import numpy as np


def population_stability_index(
    expected: np.ndarray, actual: np.ndarray, *, n_bins: int = 10
) -> float:
    """Symmetric PSI on histogram bins of ``[0, 1]``-bounded scores.

    ``expected`` and ``actual`` are 1-D arrays of participation propensity or
    similar bounded scores; both are histogrammed on shared bins.

    Args:
        expected: Reference distribution sample (1-D).
        actual: Comparison distribution sample (1-D).
        n_bins: Number of equal-width bins spanning ``[0, 1]``.

    Returns:
        PSI statistic (float). Returns ``0.0`` if either array is empty.

    Raises:
        None: This function does not raise for typical finite numeric inputs.

    Example:
        >>> import numpy as np
        >>> population_stability_index(np.array([0.1, 0.9]), np.array([0.2, 0.8])) >= 0.0
        True
    """
    e = np.asarray(expected, dtype=float).ravel()
    a = np.asarray(actual, dtype=float).ravel()
    if e.size == 0 or a.size == 0:
        return 0.0
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    e_cnt, _ = np.histogram(e, bins=bins)
    a_cnt, _ = np.histogram(a, bins=bins)
    e_pct = (e_cnt + 1e-6) / (e_cnt.sum() + 1e-6 * n_bins)
    a_pct = (a_cnt + 1e-6) / (a_cnt.sum() + 1e-6 * n_bins)
    return float(np.sum((a_pct - e_pct) * np.log(a_pct / e_pct)))

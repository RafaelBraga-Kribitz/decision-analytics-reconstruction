"""Small-sample honesty helpers shared by the exit model and walk-forward (F-085).

``EXIT_MIN_RELIABLE_WAVES`` is the single source for the exit quick-count
reliability floor cited in METHODOLOGY.md; below it the model still runs but
every output row is flagged ``low_n``. ``exact_binomial_ci`` attaches the
Clopper-Pearson interval to any k/n coverage figure so small-n coverage is
never quoted without its uncertainty.
"""

from __future__ import annotations

from scipy.stats import binomtest

EXIT_MIN_RELIABLE_WAVES = 5


def is_low_n(n_waves: int) -> bool:
    """True when an exit fit has fewer waves than the documented reliability floor."""
    return n_waves < EXIT_MIN_RELIABLE_WAVES


def exact_binomial_ci(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Clopper-Pearson interval for k successes in n trials; (nan, nan) when n == 0."""
    if n == 0:
        return float("nan"), float("nan")
    ci = binomtest(k, n).proportion_ci(confidence_level=level, method="exact")
    return float(ci.low), float(ci.high)

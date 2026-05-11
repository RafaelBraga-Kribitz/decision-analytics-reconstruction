"""Module C — Bias-aware forecasting and scenario engine (scaffold).

Bayesian poll aggregation (PyMC), Monte Carlo scenarios, and calibration
series gates live here. Downstream consumers read Module A/B contract
artifacts under ``schema_contracts/``.
"""

from module_c_forecasting_scenarios._version import __version__

__all__ = ["__version__"]

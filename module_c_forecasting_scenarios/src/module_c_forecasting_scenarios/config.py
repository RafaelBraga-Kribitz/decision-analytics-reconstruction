"""Shared configuration loader for Module C.

Single entry point for reading pymc_sampler.yaml — no model-level imports.
All callers (tracking, exit, geo, validation) use this function so the
sampler config is always read from one place and heavy dependencies (pymc,
arviz) are never pulled in by lightweight consumers like the geo module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from module_c_forecasting_scenarios.paths import module_config_dir


def load_sampler_config() -> dict[str, Any]:  # Any: yaml.safe_load returns untyped structures
    """Load and return the pymc_sampler.yaml config dict.

    Returns:
        Dict of sampler settings keyed by YAML field names.

    Raises:
        FileNotFoundError: If ``config/pymc_sampler.yaml`` is missing.
    """
    path: Path = module_config_dir() / "pymc_sampler.yaml"
    with open(path) as f:
        return yaml.safe_load(f)

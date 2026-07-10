#!/usr/bin/env python3
"""IMP-B01 static check: every Module B objective coefficient has a provenance entry.

Enumerates the hand-set objective-coefficient families used by
``module_b_resource_allocation`` — ``_TIER_PENALTY`` and
``_SCENARIO_WEEK_WEIGHTS`` (models/allocation.py), the diminishing-returns
triples ``_SAT_SHARE``/``_INFLECTION_PCT``/``_K_SHAPE``
(features/diminishing_returns.py), and ``COVERAGE_LOWER_BOUND_PCT``
(constants.py) — directly from the code, then asserts that
``config/allocation_parameter_provenance.yaml``:

  1. covers every coefficient (no code value is absent from the manifest),
  2. carries no phantom entries (no manifest value is absent from the code),
  3. records a value that matches the code value exactly, and
  4. tags each with a provenance drawn from ``constants.VALID_PROVENANCE``.

The manifest documents *that* these coefficients are unmeasured; this check
guarantees the documentation can never silently fall out of sync with the
constants the MILP actually optimizes against.

Run standalone:
    poetry run python scripts/check_allocation_parameter_provenance.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
_MANIFEST = (
    REPO_ROOT / "module_b_resource_allocation" / "config" / "allocation_parameter_provenance.yaml"
)

from module_b_resource_allocation.constants import (  # noqa: E402 -- after REPO_ROOT setup
    COVERAGE_LOWER_BOUND_PCT,
    VALID_PROVENANCE,
)
from module_b_resource_allocation.features.diminishing_returns import (  # noqa: E402 -- after REPO_ROOT setup
    _INFLECTION_PCT,
    _K_SHAPE,
    _SAT_SHARE,
)
from module_b_resource_allocation.models.allocation import (  # noqa: E402 -- after REPO_ROOT setup
    _SCENARIO_WEEK_WEIGHTS,
    _TIER_PENALTY,
)

_TOL = 1e-9


def _code_coefficients() -> dict[str, float]:
    """Flatten every hand-set objective coefficient to a ``dotted.key -> value`` map."""
    coeffs: dict[str, float] = {}
    for tier, val in _TIER_PENALTY.items():
        coeffs[f"tier_penalty.{tier}"] = float(val)
    for scen, curve in _SCENARIO_WEEK_WEIGHTS.items():
        for phase in ("early", "late"):
            coeffs[f"scenario_week_weight.{scen}.{phase}"] = float(curve[phase])
    for ch in _SAT_SHARE:
        coeffs[f"diminishing_returns.{ch}.sat_share"] = float(_SAT_SHARE[ch])
        coeffs[f"diminishing_returns.{ch}.inflection_pct"] = float(_INFLECTION_PCT[ch])
        coeffs[f"diminishing_returns.{ch}.k_shape"] = float(_K_SHAPE[ch])
    coeffs["coverage_lower_bound_pct"] = float(COVERAGE_LOWER_BOUND_PCT)
    return coeffs


def _manifest_entries(manifest: dict) -> dict[str, dict]:
    """Flatten the manifest to a ``dotted.key -> {value, provenance, source}`` map."""
    fams = manifest.get("coefficient_families", {})
    out: dict[str, dict] = {}
    for tier, e in fams.get("tier_penalty", {}).get("values", {}).items():
        out[f"tier_penalty.{tier}"] = e
    for key, e in fams.get("scenario_week_weight", {}).get("values", {}).items():
        out[f"scenario_week_weight.{key}"] = e
    for ch, triple in fams.get("diminishing_returns", {}).get("channels", {}).items():
        for param, e in triple.items():
            out[f"diminishing_returns.{ch}.{param}"] = e
    cov = fams.get("coverage_lower_bound_pct")
    if cov is not None:
        out["coverage_lower_bound_pct"] = cov
    return out


def _entry_gaps(key: str, value: float, entry: dict | None) -> list[str]:
    """Validate one manifest entry against its code coefficient."""
    if entry is None:
        return [f"coefficient {key}={value:g} has no provenance entry"]
    gaps: list[str] = []
    if abs(float(entry.get("value")) - value) > _TOL:
        gaps.append(f"{key}: manifest value {entry.get('value')} != code value {value:g}")
    if entry.get("provenance") not in VALID_PROVENANCE:
        gaps.append(
            f"{key}: provenance {entry.get('provenance')!r} not in {sorted(VALID_PROVENANCE)}"
        )
    if not str(entry.get("source", "")).strip():
        gaps.append(f"{key}: empty source string")
    return gaps


def _all_gaps(code: dict[str, float], entries: dict[str, dict]) -> list[str]:
    gaps: list[str] = []
    for key, value in code.items():
        gaps.extend(_entry_gaps(key, value, entries.get(key)))
    gaps.extend(
        f"manifest names {key} which no longer exists in the code"
        for key in entries
        if key not in code
    )
    return gaps


def main() -> int:
    if not _MANIFEST.is_file():
        print(f"[FAIL] check_allocation_parameter_provenance.py: missing {_MANIFEST}")
        return 1

    manifest = yaml.safe_load(_MANIFEST.read_text(encoding="utf-8")) or {}
    code = _code_coefficients()
    gaps = _all_gaps(code, _manifest_entries(manifest))

    if gaps:
        print(
            f"[FAIL] check_allocation_parameter_provenance.py: {len(gaps)} gap(s) between "
            "code coefficients and the provenance manifest:"
        )
        for g in gaps:
            print(f"       {g}")
        return 1
    print(
        f"[PASS] check_allocation_parameter_provenance.py: {len(code)} objective "
        "coefficients all carry a matching provenance entry"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

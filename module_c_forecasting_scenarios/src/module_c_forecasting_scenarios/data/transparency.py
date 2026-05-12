"""Transparency scorer: phi in (0, 1] from ficha + methodological disclosure pillars."""

from __future__ import annotations

PHI_MIN: float = 0.08
PHI_MAX: float = 1.0
PHI_MISSING_TWO_OR_MORE: float = 0.12


def compute_phi_transparency(
    has_ficha: bool,
    sample_size_known: bool,
    field_window_known: bool,
    mode_known: bool,
) -> float:
    pillars = (sample_size_known, field_window_known, mode_known)
    n_ok = sum(1 for p in pillars if p)
    base = 0.55 if not has_ficha else 0.85
    step = 0.12
    phi = base + step * n_ok
    if n_ok <= 1:
        phi = min(phi, PHI_MISSING_TWO_OR_MORE + 0.25)
    if n_ok == 0:
        phi = PHI_MISSING_TWO_OR_MORE
    return float(max(PHI_MIN, min(PHI_MAX, phi)))


def compute_tau_eff(phi: float, tau_base: float = 1.0) -> float:
    return float(max(1e-6, phi * tau_base))

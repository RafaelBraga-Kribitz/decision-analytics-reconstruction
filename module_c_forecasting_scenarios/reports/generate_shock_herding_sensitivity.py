#!/usr/bin/env python3
"""Generate the shock/herding parameter bucket-reassignment sensitivity artifact.

IMP-C04 (audit C5) acceptance criterion 3: publish a sensitivity artifact
showing, per hypothesis parameter, the fraction of polls whose canonical
scenario-bucket assignment changes under +/-25% and +/-50% perturbation. Any
parameter whose +/-25% perturbation reassigns more than 20% of polls is
flagged `assignment-critical`.

Deterministic and dependency-light: uses the canonical fixture
(`tests/fixtures/polls_raw_fixture.csv`), which is the only tracking dataset
committed in this repository, run through the same cleaning pipeline every
other Module C test uses. No RNG is involved anywhere in this script — bucket
reassignment is a pure function of (poll row, parameter set).

Run: ``poetry run python module_c_forecasting_scenarios/reports/generate_shock_herding_sensitivity.py``
Writes: ``module_c_forecasting_scenarios/reports/shock_herding_sensitivity.md``
"""

from __future__ import annotations

import copy
import hashlib
import logging
import sys
from pathlib import Path

# Local package import — this script lives outside `src/`, so make the module
# importable without requiring the package to be pip-installed.
_MODULE_ROOT = Path(__file__).resolve().parents[1]
_SRC = _MODULE_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import yaml  # noqa: E402

from module_c_forecasting_scenarios.data.cleaning_pipeline import (  # noqa: E402
    _load_m_star,
    clean_raw_polls,
)
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv  # noqa: E402
from module_c_forecasting_scenarios.features.herding_weights import (  # noqa: E402
    load_herding_config,
    rho_herd_for_row,
)
from module_c_forecasting_scenarios.features.shock_scores import (  # noqa: E402
    load_shock_params,
    scenario_bucket_for_margin,
    shock_score_s,
)
from module_c_forecasting_scenarios.paths import module_config_dir, repo_root  # noqa: E402

FIXTURE = _MODULE_ROOT / "tests" / "fixtures" / "polls_raw_fixture.csv"
OUT_MD = Path(__file__).resolve().parent / "shock_herding_sensitivity.md"
OUT_CSV = Path(__file__).resolve().parent / "shock_herding_sensitivity.csv"

PERTURBATIONS: tuple[float, ...] = (-0.50, -0.25, 0.25, 0.50)
ASSIGNMENT_CRITICAL_FRACTION_AT_25PCT = 0.20

# Bucket-assignment-relevant shock_params.yaml keys.
_THRESHOLD_PARAMS: tuple[str, ...] = (
    "m_star_extreme_pp",
    "phi_opaque_threshold",
    "rho_herd_threshold",
)

# Named herding-covariance parameters and the (window, [groups-to-perturb-together])
# cells they control. `march_window` is the only window whose elevated/baseline
# cells differ (0.55 vs 0.35); `april_window` and `outside_window` share a single
# value across both groups (0.25 / 0.05 respectively, config/herding_groups.yaml),
# so perturbing "the April covariance" means perturbing both group cells together
# to keep the parameter's semantics (one shared value) intact under perturbation.
_HERDING_PARAMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("herding_covariance_march_elevated", "march_window", ("elevated",)),
    ("herding_covariance_march_baseline", "march_window", ("baseline",)),
    ("herding_covariance_april", "april_window", ("elevated", "baseline")),
    ("herding_covariance_outside", "outside_window", ("elevated", "baseline")),
)

# Continuous-score-only weights (do not enter scenario_bucket_for_margin at all).
_LAMBDA_PARAMS: tuple[str, ...] = ("lambda1", "lambda2", "lambda3")


def _config_hash() -> str:
    """Sha256 over shock_params.yaml + herding_groups.yaml bytes (stale-artifact guard).

    CRLF is normalized to LF so the hash is checkout-independent: autocrlf
    working trees materialize these YAMLs with CRLF on Windows (issue #168).
    """
    h = hashlib.sha256()
    for name in ("shock_params.yaml", "herding_groups.yaml"):
        h.update((module_config_dir() / name).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def _load_canonical_rows() -> list[dict[str, object]]:
    """Load the canonical fixture and return one dict per tracking poll row."""
    raw = load_raw_polls_csv(FIXTURE)
    tracking, _exit = clean_raw_polls(raw, "A")
    m_star = _load_m_star("A")
    rows: list[dict[str, object]] = []
    for _, r in tracking.iterrows():
        rows.append(
            {
                "m_poll_pp": float(r["m_poll_pp"]),
                "m_star_pp": m_star,
                "phi": float(r["phi_transparency"]),
                "publication_date": r["publication_date"],
                "carrier": r.get("conglomerate_id"),
                "baseline_bucket": str(r["scenario_bucket"]),
            }
        )
    return rows


def _reassignment_fraction(
    rows: list[dict[str, object]],
    *,
    shock_params_override: dict[str, object] | None = None,
    herding_config_override: dict[str, object] | None = None,
) -> float:
    """Fraction of rows whose bucket assignment changes under an override."""
    changed = 0
    for row in rows:
        rho = rho_herd_for_row(
            row["publication_date"],  # type: ignore[arg-type]
            row["carrier"],  # type: ignore[arg-type]
            config=herding_config_override,
        )
        bucket = scenario_bucket_for_margin(
            row["m_poll_pp"],  # type: ignore[arg-type]
            row["m_star_pp"],  # type: ignore[arg-type]
            row["phi"],  # type: ignore[arg-type]
            rho,
            params=shock_params_override,
        )
        if bucket != row["baseline_bucket"]:
            changed += 1
    return changed / len(rows) if rows else 0.0


def _threshold_param_sensitivity(
    rows: list[dict[str, object]], baseline_params: dict[str, object]
) -> dict[str, dict[float, float]]:
    out: dict[str, dict[float, float]] = {}
    for key in _THRESHOLD_PARAMS:
        out[key] = {}
        base_value = float(baseline_params[key])  # type: ignore[arg-type]
        for pct in PERTURBATIONS:
            perturbed = dict(baseline_params)
            perturbed[key] = base_value * (1.0 + pct)
            out[key][pct] = _reassignment_fraction(rows, shock_params_override=perturbed)
    return out


def _herding_cell_sensitivity(
    rows: list[dict[str, object]], baseline_herding: dict[str, object]
) -> dict[str, dict[float, float]]:
    out: dict[str, dict[float, float]] = {}
    matrix = baseline_herding["covariance_matrix"]  # type: ignore[index]
    for label, window, groups in _HERDING_PARAMS:
        base_value = float(matrix[window][groups[0]])  # type: ignore[index]
        out[label] = {}
        for pct in PERTURBATIONS:
            perturbed = copy.deepcopy(baseline_herding)
            for group in groups:
                perturbed["covariance_matrix"][window][group] = base_value * (1.0 + pct)  # type: ignore[index]
            out[label][pct] = _reassignment_fraction(rows, herding_config_override=perturbed)
    return out


def _lambda_score_sensitivity(
    rows: list[dict[str, object]], baseline_params: dict[str, object]
) -> dict[str, dict[float, float]]:
    """Mean relative delta in continuous shock_score_s under +/- lambda perturbation.

    lambda1/2/3 do not appear in scenario_bucket_for_margin's signature at all,
    so their bucket-reassignment fraction is definitionally 0.0 for every
    perturbation level — reported honestly as such, with the continuous-score
    sensitivity reported instead as the parameter's genuine impact surface.
    """
    out: dict[str, dict[float, float]] = {}
    for key in _LAMBDA_PARAMS:
        out[key] = {}
        base_value = float(baseline_params[key])  # type: ignore[arg-type]
        baseline_scores = [
            shock_score_s(
                row["m_poll_pp"],  # type: ignore[arg-type]
                row["m_star_pp"],  # type: ignore[arg-type]
                row["phi"],  # type: ignore[arg-type]
                row["publication_date"],  # type: ignore[arg-type]
                row["carrier"],  # type: ignore[arg-type]
                params=baseline_params,
            )
            for row in rows
        ]
        for pct in PERTURBATIONS:
            perturbed = dict(baseline_params)
            perturbed[key] = base_value * (1.0 + pct)
            perturbed_scores = [
                shock_score_s(
                    row["m_poll_pp"],  # type: ignore[arg-type]
                    row["m_star_pp"],  # type: ignore[arg-type]
                    row["phi"],  # type: ignore[arg-type]
                    row["publication_date"],  # type: ignore[arg-type]
                    row["carrier"],  # type: ignore[arg-type]
                    params=perturbed,
                )
                for row in rows
            ]
            deltas = [
                abs(p - b) / b if b > 0 else 0.0
                for p, b in zip(perturbed_scores, baseline_scores, strict=True)
            ]
            out[key][pct] = sum(deltas) / len(deltas) if deltas else 0.0
    return out


def _render_markdown(
    threshold_sens: dict[str, dict[float, float]],
    herding_sens: dict[str, dict[float, float]],
    lambda_sens: dict[str, dict[float, float]],
    n_rows: int,
    config_hash: str,
) -> str:
    lines: list[str] = []
    lines.append("# Shock & herding parameter sensitivity (IMP-C04 / audit C5)")
    lines.append("")
    lines.append(
        "Generated by `module_c_forecasting_scenarios/reports/generate_shock_herding_sensitivity.py` "
        "against the canonical fixture (`tests/fixtures/polls_raw_fixture.csv`, "
        f"{n_rows} tracking polls). Deterministic — no RNG."
    )
    lines.append("")
    lines.append(f"**Config hash (shock_params.yaml + herding_groups.yaml):** `{config_hash}`")
    lines.append("")
    lines.append(
        "Every parameter perturbed here carries a `hypothesis` provenance row in "
        "`config/shock_params.yaml` / `config/herding_groups.yaml` — none is fit against a "
        "historical polling-error dataset. This artifact is the pre-registered sensitivity "
        "envelope that accompanies that disclosure."
    )
    lines.append("")
    lines.append(
        "## Bucket-assignment reassignment fraction "
        f"(flagged `assignment-critical` when either +/-25% perturbation reassigns > "
        f"{ASSIGNMENT_CRITICAL_FRACTION_AT_25PCT:.0%} of polls)"
    )
    lines.append("")
    lines.append("| Parameter | -50% | -25% | +25% | +50% | assignment-critical? |")
    lines.append("|---|---|---|---|---|---|")
    critical: list[str] = []
    for label, sens in {**threshold_sens, **herding_sens}.items():
        crit = (
            sens.get(0.25, 0.0) > ASSIGNMENT_CRITICAL_FRACTION_AT_25PCT
            or sens.get(-0.25, 0.0) > ASSIGNMENT_CRITICAL_FRACTION_AT_25PCT
        )
        if crit:
            critical.append(label)
        lines.append(
            f"| `{label}` | {sens.get(-0.50, 0.0):.1%} | {sens.get(-0.25, 0.0):.1%} | "
            f"{sens.get(0.25, 0.0):.1%} | {sens.get(0.50, 0.0):.1%} | {'YES' if crit else 'no'} |"
        )
    lines.append("")
    if critical:
        lines.append(
            "**Disclosure requirement:** every scenario-level chart/table consuming bucket "
            f"assignments must disclose this assignment-critical list: {', '.join(sorted(critical))}."
        )
    else:
        lines.append(
            "No parameter is `assignment-critical` on the canonical fixture at the current "
            "values — bucket assignment is stable under +/-25% perturbation of every threshold."
        )
    lines.append("")
    lines.append(
        "## Continuous shock-score sensitivity (lambda1/2/3 — do not enter bucket assignment)"
    )
    lines.append("")
    lines.append(
        "`scenario_bucket_for_margin` never reads `lambda1`/`lambda2`/`lambda3` — they only "
        "scale the continuous `shock_score_s` (used for within-bucket Monte Carlo sampling "
        "weights, IMP-C08). Their bucket-reassignment fraction is therefore *definitionally* "
        "0.0 at every perturbation level; the mean relative change in `shock_score_s` is "
        "reported instead as their genuine sensitivity surface."
    )
    lines.append("")
    lines.append("| Parameter | mean |delta score| / score at -50% | -25% | +25% | +50% |")
    lines.append("|---|---|---|---|---|")
    for label, sens in lambda_sens.items():
        lines.append(
            f"| `{label}` | {sens.get(-0.50, 0.0):.1%} | {sens.get(-0.25, 0.0):.1%} | "
            f"{sens.get(0.25, 0.0):.1%} | {sens.get(0.50, 0.0):.1%} |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_csv(
    threshold_sens: dict[str, dict[float, float]],
    herding_sens: dict[str, dict[float, float]],
    lambda_sens: dict[str, dict[float, float]],
) -> str:
    rows = ["parameter,metric,pct_perturbation,value"]
    for label, sens in {**threshold_sens, **herding_sens}.items():
        for pct, value in sorted(sens.items()):
            rows.append(f"{label},bucket_reassignment_fraction,{pct},{value}")
    for label, sens in lambda_sens.items():
        for pct, value in sorted(sens.items()):
            rows.append(f"{label},mean_relative_score_delta,{pct},{value}")
    return "\n".join(rows) + "\n"


def main() -> int:
    # This sweep deliberately re-resolves every row's herding group dozens of
    # times (once per perturbation level); the fixture's ABC/Nacion Media
    # carriers are legitimately unmapped (only Vierci/ICA are in
    # herding_groups.yaml) and would otherwise log one warning per call. The
    # per-call warning is the correct behavior for a real pipeline run; here
    # it is redundant noise, so raise the threshold for the duration of the sweep.
    logging.getLogger("module_c_forecasting_scenarios.features.herding_weights").setLevel(
        logging.ERROR
    )
    rows = _load_canonical_rows()
    baseline_params = load_shock_params()
    baseline_herding = load_herding_config()

    threshold_sens = _threshold_param_sensitivity(rows, baseline_params)
    herding_sens = _herding_cell_sensitivity(rows, baseline_herding)
    lambda_sens = _lambda_score_sensitivity(rows, baseline_params)

    md = _render_markdown(threshold_sens, herding_sens, lambda_sens, len(rows), _config_hash())
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_CSV.write_text(_render_csv(threshold_sens, herding_sens, lambda_sens), encoding="utf-8")

    def _display(path: Path) -> str:
        try:
            return str(path.relative_to(repo_root()))
        except ValueError:
            return str(path)

    print(f"[PASS] wrote {_display(OUT_MD)} and {_display(OUT_CSV)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

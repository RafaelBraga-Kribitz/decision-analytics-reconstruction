#!/usr/bin/env python3
"""Render the README's "decision at a glance" panel from committed results only.

One figure, drawn on the Braga design system v2.1 (bk-viz 2.0.0, ``bk_theme``): a KPI
row with the numbers a campaign manager acts on, the finding as the headline, and
the per-department budget shift of the week-8 decision replay as the chart.

Inputs (all committed, nothing is re-solved or re-simulated here):

* ``reports/decision_replay_results.json`` - week-8 replay totals and the
  per-department baseline vs replay spend (``scripts/generate_decision_replay.py``).
* ``reports/golden_metrics.json`` - Module B budget envelope.
* ``reports/module_c/walk_forward_loo_metrics.json`` - held-out poll coverage.
* ``module_c_forecasting_scenarios/config/calibration.yaml`` - verified margin.

Output: ``reports/decision/decision_kpi_panel.png``, registered in
``governance/FIGURE_MANIFEST.yaml`` by ``scripts/generate_figure_manifest.py``.

The replay is a disclosed scenario (one hand-set solver lever, illustrative
fixture posterior), so the figure carries the ILLUSTRATIVE tag. bk-viz ships
euro formatters only; this script formats US dollars itself.

Run::

    poetry run python scripts/generate_decision_kpi_panel.py
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import bk_theme as bk
import yaml
from matplotlib.ticker import FuncFormatter, MaxNLocator

REPO_ROOT = Path(__file__).resolve().parent.parent
REPLAY = REPO_ROOT / "reports" / "decision_replay_results.json"
GOLDEN = REPO_ROOT / "reports" / "golden_metrics.json"
LOO = REPO_ROOT / "reports" / "module_c" / "walk_forward_loo_metrics.json"
CALIBRATION = REPO_ROOT / "module_c_forecasting_scenarios" / "config" / "calibration.yaml"
OUT_STEM = REPO_ROOT / "reports" / "decision" / "decision_kpi_panel"


def fmt_usd_k(v: float) -> str:
    """Signed US dollars in thousands, e.g. ``-$255k`` / ``+$323k``."""
    sign = "-" if v < 0 else "+" if v > 0 else ""
    return f"{sign}${abs(v) / 1_000:,.0f}k"


def fmt_usd_axis(v: float, _pos: int | None = None) -> str:
    """Axis tick variant of :func:`fmt_usd_k` without a plus sign on zero."""
    if abs(v) < 0.5:
        return "$0"
    return fmt_usd_k(v)


def load_inputs() -> dict:
    """Read the committed result files and return the values the panel shows."""
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    loo = json.loads(LOO.read_text(encoding="utf-8"))
    calib = yaml.safe_load(CALIBRATION.read_text(encoding="utf-8"))

    series = calib["series"]
    totals = replay["totals"]
    envelope = float(golden["module_b"]["total_budget_usd"])
    if abs(envelope - float(totals["budget_envelope_usd"])) > 1.0:
        raise SystemExit("golden_metrics and decision_replay disagree on the budget envelope")

    swing_rows = [d for d in replay["departments"] if d["tier"] == "swing"]
    shifted = -sum(d["delta_usd"] for d in swing_rows)
    if abs(shifted - float(totals["usd_shifted_off_swing"])) > 1.0:
        raise SystemExit("per-department swing deltas do not sum to usd_shifted_off_swing")

    return {
        "departments": sorted(replay["departments"], key=lambda d: d["delta_usd"]),
        "n_swing": len(swing_rows),
        "shifted_usd": float(totals["usd_shifted_off_swing"]),
        "value_pct": float(totals["belief_weighted_value_of_update_pct"]),
        "envelope_usd": envelope,
        "margin_pp": float(calib["anchors"][series]["margin_m_star_pp"]),
        "loo_k": int(loo["coverage_95pct_k"]),
        "loo_n": int(loo["n_holdouts"]),
        "plan_lead_pp": float(replay["posterior"]["plan"]["margin_mean_pp"]),
        "week8_lead_pp": float(replay["posterior"]["replay"]["margin_mean_pp"]),
        "seed": replay["solver_seed"],
    }


def build_panel(v: dict) -> list[Path]:
    """Draw the decision panel and write it as PNG."""
    with warnings.catch_warnings():
        # bk-viz 2 ships BKribitz / BKribitz Mono and registers them itself; the
        # only warnings left are v1-alias deprecations, none of which apply here.
        warnings.simplefilter("ignore", DeprecationWarning)
        bk.apply("light", grid="x")

    kpis = [
        {
            "label": "Moved off swing",
            "value": f"${v['shifted_usd'] / 1_000:,.0f}k",
            "note": f"from {v['n_swing']} swing departments at week 8",
            "accent": True,
        },
        {
            "label": "Value of updating",
            "value": f"+{v['value_pct']:.2f}%",
            "note": "persuasion-weighted contacts vs keeping the plan",
        },
        {
            "label": "Budget envelope",
            "value": f"${v['envelope_usd'] / 1_000_000:.2f}M",
            "note": "same envelope before and after",
        },
        {
            "label": "Held-out polls",
            "value": f"{v['loo_k']} of {v['loo_n']}",
            "note": "inside the 95% band, leave-one-wave-out",
        },
    ]
    finding = (
        f"When the tracked lead widened at week 8, re-solving moves "
        f"${v['shifted_usd'] / 1_000:,.0f}k off the swing departments"
    )
    context = (
        f"Change in planned spend per department, week-8 replay versus the plan-time "
        f"allocation. Tracked lead {v['plan_lead_pp']:.1f} pp at week 1, "
        f"{v['week8_lead_pp']:.1f} pp at week 8 (posterior mean). Verified 2018 result: "
        f"+{v['margin_pp']:.2f} pp. Dark bars: the {v['n_swing']} swing departments."
    )

    fig, ax = bk.decision_panel(
        kpis=kpis, finding=finding, context=context, rows=10, left=0.17, bottom=0.155
    )

    depts = v["departments"]
    labels = [d["department"] for d in depts]
    deltas = [d["delta_usd"] for d in depts]
    colors = [bk.c("ink") if d["tier"] == "swing" else bk.c("mid") for d in depts]
    ax.barh(range(len(depts)), deltas, color=colors, height=0.68)
    ax.set_yticks(range(len(depts)), labels)
    ax.invert_yaxis()
    ax.axvline(0, color=bk.c("ink-2"), lw=bk.HAIRLINE_PT)
    bk.strip_chrome(ax, keep=("bottom",))
    ax.xaxis.set_major_formatter(FuncFormatter(fmt_usd_axis))
    ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
    span = max(abs(x) for x in deltas)
    ax.set_xlim(-span * 1.32, span * 1.32)
    for i, x in enumerate(deltas):
        if abs(x) < 1:
            text, ha, off = "no change", "left", 6
        else:
            text, ha, off = fmt_usd_k(x), ("right" if x < 0 else "left"), (-6 if x < 0 else 6)
        ax.annotate(
            text,
            xy=(x, i),
            xytext=(off, 0),
            textcoords="offset points",
            ha=ha,
            va="center",
            color=bk.c("ink"),
            fontproperties=bk.font("mono", "regular", "mono"),
        )

    bk.footer(
        fig,
        source="committed JSON in reports/ (replay, golden, LOO)",
        run_id=f"seed {v['seed']}",
        tag="ILLUSTRATIVE",
        note=(
            "Scenario replay: one disclosed solver lever (swing-tier weight) set from an "
            "illustrative tracking posterior. Not a causal claim. At the low edge of the 94% "
            "interval the shift reverses."
        ),
        left=0.17,
    )
    return bk.save(fig, OUT_STEM, formats=("png",), dpi=120)


def main() -> int:
    """Entry point: load committed inputs, render, report the written path."""
    written = build_panel(load_inputs())
    for p in written:
        print(f"[generate_decision_kpi_panel] wrote {p.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

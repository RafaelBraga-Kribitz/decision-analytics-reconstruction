#!/usr/bin/env python3
"""Generate a SHAP summary bar plot for the propensity model (optional extra).

Requires: ``poetry install --extras explainability``

Writes: ``reports/module_a/shap_summary.png`` (create directory if missing).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        import shap
        from sklearn.linear_model import LogisticRegression
    except ImportError:
        print("Install extras: poetry install --extras explainability matplotlib", file=sys.stderr)
        return 2

    rng = np.random.default_rng(42)
    x = rng.normal(size=(800, 6))
    y = (x[:, 0] + 0.2 * rng.normal(size=800) > 0).astype(int)
    model = LogisticRegression(max_iter=200).fit(x, y)
    explainer = shap.LinearExplainer(model, x[:200])
    sv = explainer(x[:200])
    out_dir = ROOT / "reports" / "module_a"
    out_dir.mkdir(parents=True, exist_ok=True)
    shap.summary_plot(sv, show=False)
    plt.tight_layout()
    path = out_dir / "shap_summary.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Verify no function exceeds the CRAP score threshold.

CRAP(F) = C² × (1 − COV)³ + C
  C   = cyclomatic complexity (via radon)
  COV = line coverage fraction for the function (via coverage.py)

Gate: F-CRAP-SCORE (crap_violation category)

Run with --baseline to print the top-10 worst CRAP scores without gating.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate


def _load_threshold() -> float:
    try:
        import yaml
        cfg_path = REPO_ROOT / "config" / "quality_gates.yaml"
        if cfg_path.exists():
            data = yaml.safe_load(cfg_path.read_text()) or {}
            return float(data.get("crap", {}).get("max_score", 30))
    except Exception:
        pass
    return 30.0


def _find_py_files() -> list[Path]:
    dirs = [REPO_ROOT / d for d in ("src", "scripts") if (REPO_ROOT / d).is_dir()]
    files = []
    for d in dirs:
        files.extend(d.rglob("*.py"))
    return [f for f in files if "test" not in f.parts and "governance" not in f.parts]


def _fn_coverage(cov, path: Path, start: int, end: int) -> float:
    try:
        analysis = cov._analyze(str(path))
        executed = set(analysis.executed)
        func_lines = list(range(start, end + 1))
        if not func_lines:
            return 1.0
        return len([ln for ln in func_lines if ln in executed]) / len(func_lines)
    except Exception:
        return 0.0


def _compute_scores(files: list[Path]) -> list[tuple[float, str, int]]:
    import coverage as cov_lib
    from radon.complexity import cc_visit

    cov = cov_lib.Coverage(data_file=str(REPO_ROOT / ".coverage"))
    try:
        cov.load()
        cov_loaded = True
    except Exception:
        cov_loaded = False

    scores = []
    for path in files:
        try:
            blocks = cc_visit(path.read_text())
        except (SyntaxError, OSError):
            continue
        for block in blocks:
            c = block.complexity
            end = getattr(block, "endline", block.lineno)
            cov_pct = _fn_coverage(cov, path, block.lineno, end) if cov_loaded else 0.0
            crap = c ** 2 * (1 - cov_pct) ** 3 + c
            scores.append((crap, f"{path.relative_to(REPO_ROOT)}:{block.name}", c))
    return sorted(scores, reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()

    try:
        import radon  # noqa: F401
    except ImportError:
        print("[SKIP] check_crap_score.py: radon not installed (pip install radon)")
        return 0

    try:
        import coverage  # noqa: F401
    except ImportError:
        print("[SKIP] check_crap_score.py: coverage not installed (pip install coverage)")
        return 0

    files = _find_py_files()
    if not files:
        print("[SKIP] check_crap_score.py: no Python source files found in src/ or scripts/")
        return 0

    scores = _compute_scores(files)

    if args.baseline:
        print("[BASELINE] check_crap_score.py: top-10 worst CRAP scores")
        for crap, name, c in scores[:10]:
            print(f"           {crap:6.1f}  {name}  (complexity={c})")
        suggested = int(scores[0][0]) + 5 if scores else 30
        print(f"           Suggested quality_gates.crap.max_score: {suggested}")
        return 0

    threshold = _load_threshold()
    violations = [(crap, name) for crap, name, _ in scores if crap > threshold]
    gap = (
        f"{len(violations)} function(s) exceed CRAP {threshold}: "
        f"{violations[0][1]} (score={violations[0][0]:.1f})"
        if violations else ""
    )
    return gate("F-CRAP-SCORE", "check_crap_score.py", not violations, gap)


if __name__ == "__main__":
    sys.exit(main())

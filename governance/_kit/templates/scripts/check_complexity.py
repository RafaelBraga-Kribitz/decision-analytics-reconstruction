"""Verify no function exceeds the cyclomatic complexity threshold.

Uses radon to measure McCabe complexity. Functions with a score above
quality_gates.complexity.max_per_function are reported as violations.

Gate: F-COMPLEXITY-VIOLATION (complexity_violation category)

Run with --baseline to print the current worst-case complexity without gating.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate


def _load_threshold() -> int:
    try:
        import yaml
        cfg_path = REPO_ROOT / "config" / "quality_gates.yaml"
        if cfg_path.exists():
            data = yaml.safe_load(cfg_path.read_text()) or {}
            return int(data.get("complexity", {}).get("max_per_function", 6))
    except Exception:
        pass
    return 6


def _find_py_files() -> list[Path]:
    dirs = [REPO_ROOT / d for d in ("src", "scripts") if (REPO_ROOT / d).is_dir()]
    files = []
    for d in dirs:
        files.extend(d.rglob("*.py"))
    return [f for f in files if "test" not in f.parts and "governance" not in f.parts]


def _check_files(files: list[Path], threshold: int) -> list[tuple[str, str, int]]:
    from radon.complexity import cc_visit
    violations = []
    for path in files:
        try:
            results = cc_visit(path.read_text())
        except SyntaxError:
            continue
        for block in results:
            if block.complexity > threshold:
                violations.append((str(path.relative_to(REPO_ROOT)), block.name, block.complexity))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()

    try:
        import radon  # noqa: F401
    except ImportError:
        print("[SKIP] check_complexity.py: radon not installed (pip install radon)")
        return 0

    files = _find_py_files()
    if not files:
        print("[SKIP] check_complexity.py: no Python source files found in src/ or scripts/")
        return 0

    if args.baseline:
        from radon.complexity import cc_visit
        worst, worst_name = 0, ""
        for path in files:
            try:
                for block in cc_visit(path.read_text()):
                    if block.complexity > worst:
                        worst = block.complexity
                        worst_name = f"{path.relative_to(REPO_ROOT)}:{block.name}"
            except SyntaxError:
                continue
        print(f"[BASELINE] check_complexity.py: worst complexity = {worst} ({worst_name})")
        print(f"           Suggested quality_gates.complexity.max_per_function: {worst}")
        return 0

    threshold = _load_threshold()
    violations = _check_files(files, threshold)
    gap = (
        f"{len(violations)} function(s) exceed complexity {threshold}: "
        f"{violations[0][0]}:{violations[0][1]} (score={violations[0][2]})"
        if violations else ""
    )
    return gate("F-COMPLEXITY-VIOLATION", "check_complexity.py", not violations, gap)


if __name__ == "__main__":
    sys.exit(main())

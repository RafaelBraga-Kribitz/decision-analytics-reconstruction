"""Verify source files and functions stay within the line-count budget.

Uses stdlib ast only — no third-party dependencies required.

Gate: F-MODULE-SIZE (module_size_violation category)

Run with --baseline to print the current worst-case sizes without gating.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate


def _load_thresholds() -> tuple[int, int]:
    try:
        import yaml
        cfg_path = REPO_ROOT / "config" / "quality_gates.yaml"
        if cfg_path.exists():
            data = yaml.safe_load(cfg_path.read_text()) or {}
            ms = data.get("module_size", {})
            return int(ms.get("max_file_lines", 250)), int(ms.get("max_function_lines", 40))
    except Exception:
        pass
    return 250, 40


def _find_py_files() -> list[Path]:
    dirs = [REPO_ROOT / d for d in ("src", "scripts") if (REPO_ROOT / d).is_dir()]
    files = []
    for d in dirs:
        files.extend(d.rglob("*.py"))
    return [f for f in files if "test" not in f.parts and "governance" not in f.parts]


def _fn_lines(node: ast.AST) -> int:
    if hasattr(node, "end_lineno") and hasattr(node, "lineno"):
        return node.end_lineno - node.lineno + 1
    return 0


def _scan(files: list[Path], max_file: int, max_fn: int) -> list[str]:
    violations = []
    for path in files:
        src = path.read_text(errors="replace")
        rel = str(path.relative_to(REPO_ROOT))
        if (lc := src.count("\n") + 1) > max_file:
            violations.append(f"{rel}: {lc} lines (max {max_file})")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if (fl := _fn_lines(node)) > max_fn:
                    violations.append(f"{rel}:{node.name}(): {fl} lines (max {max_fn})")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()

    files = _find_py_files()
    if not files:
        print("[SKIP] check_module_sizes.py: no Python source files found in src/ or scripts/")
        return 0

    if args.baseline:
        wf, wf_name, wn, wn_name = 0, "", 0, ""
        for path in files:
            src = path.read_text(errors="replace")
            if (lc := src.count("\n") + 1) > wf:
                wf, wf_name = lc, str(path.relative_to(REPO_ROOT))
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if (fl := _fn_lines(node)) > wn:
                        wn, wn_name = fl, f"{path.relative_to(REPO_ROOT)}:{node.name}"
        print(f"[BASELINE] check_module_sizes.py: worst file = {wf} lines ({wf_name})")
        print(f"           worst function = {wn} lines ({wn_name})")
        print(f"           Suggested quality_gates.module_size.max_file_lines: {wf}")
        print(f"           Suggested quality_gates.module_size.max_function_lines: {wn}")
        return 0

    max_file, max_fn = _load_thresholds()
    violations = _scan(files, max_file, max_fn)
    gap = f"{len(violations)} violation(s): {violations[0]}" if violations else ""
    return gate("F-MODULE-SIZE", "check_module_sizes.py", not violations, gap)


if __name__ == "__main__":
    sys.exit(main())

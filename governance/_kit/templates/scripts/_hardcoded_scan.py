"""Shared AST visitor for hardcoded-value detection.

Used by:
  - check_hardcoded_values.py (Python source files)
  - check_notebook_values.py (Jupyter .ipynb code cells)

Detects non-trivial numeric / date / interval literals in:
  - assignments (x = 42; self.x = 42; x[0] = 42; x, y = 1, 42)
  - augmented assignments (x += 42)
  - comparisons (if x > 42:)
  - function-call arguments (f(42), f(seed=42)) — minus allowlist
  - default parameter values (def f(seed=42))
  - dict / list / set literals (cfg = {"k": 42})

Trivial values (always allowed):
  - ints in {-1, 0, 1, 2}
  - floats in {-1.0, 0.0, 0.5, 1.0}
  - booleans

Allowlist of call names where literal positional args are routine indexers:
  range, len, slice, enumerate, zip, round, head, tail, iloc, loc, take,
  nlargest, nsmallest, sample (for n=), str.zfill, str.ljust, str.rjust.

These names are matched on the FINAL attribute name only (df.head(5) → "head").
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Iterable

TRIVIAL_INTS = {-1, 0, 1, 2}
TRIVIAL_FLOATS = {-1.0, 0.0, 0.5, 1.0}
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

INDEXER_CALLS = frozenset({
    "range", "len", "slice", "enumerate", "zip", "round",
    "head", "tail", "iloc", "loc", "take",
    "nlargest", "nsmallest", "sample",
    "zfill", "ljust", "rjust",
})


@dataclass
class Violation:
    lineno: int
    kind: str       # assign | augassign | compare | call_pos | call_kw | default | dict | list | set
    where: str      # variable name, function name, comparison op, etc.
    value: str      # repr of the literal


def _is_trivial(v: object) -> bool:
    if isinstance(v, bool):
        return True
    if isinstance(v, int) and v in TRIVIAL_INTS:
        return True
    if isinstance(v, float) and v in TRIVIAL_FLOATS:
        return True
    return False


def _is_flaggable(v: object) -> bool:
    """A constant is flaggable if it's a non-trivial int/float or a date string."""
    if _is_trivial(v):
        return False
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, str) and DATE_PATTERN.match(v):
        return True
    return False


def _call_final_name(func: ast.AST) -> str | None:
    """Return the final attribute name of a call's func: f(), df.head() -> 'head'."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _target_label(target: ast.AST) -> str:
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return _target_label(target.value) + "." + target.attr
    if isinstance(target, ast.Subscript):
        return _target_label(target.value) + "[…]"
    if isinstance(target, ast.Tuple):
        return ",".join(_target_label(e) for e in target.elts)
    return "?"


class HardcodedVisitor(ast.NodeVisitor):
    """Collects Violation objects for every flaggable literal it finds."""

    def __init__(self) -> None:
        self.violations: list[Violation] = []

    def _emit(self, lineno: int, kind: str, where: str, value: object) -> None:
        self.violations.append(Violation(lineno, kind, where, repr(value)))

    # ── Assignments ──────────────────────────────────────────────────────

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._check_rhs(target, node.value, node.lineno, "assign")
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self._check_rhs(node.target, node.value, node.lineno, "assign")
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        label = _target_label(node.target)
        if isinstance(node.value, ast.Constant) and _is_flaggable(node.value.value):
            self._emit(node.lineno, "augassign", label, node.value.value)
        self.generic_visit(node)

    def _check_rhs(self, target: ast.AST, value: ast.AST, lineno: int, kind: str) -> None:
        label = _target_label(target)
        if isinstance(value, ast.Constant) and _is_flaggable(value.value):
            self._emit(lineno, kind, label, value.value)
        elif isinstance(value, ast.Tuple) and isinstance(target, ast.Tuple):
            for tgt, val in zip(target.elts, value.elts):
                self._check_rhs(tgt, val, lineno, kind)
        elif isinstance(value, ast.Dict):
            for k, v in zip(value.keys, value.values):
                if isinstance(v, ast.Constant) and _is_flaggable(v.value):
                    key_label = k.value if isinstance(k, ast.Constant) else "?"
                    self._emit(lineno, "dict", f"{label}[{key_label!r}]", v.value)
        elif isinstance(value, (ast.List, ast.Set)):
            kind_name = "list" if isinstance(value, ast.List) else "set"
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and _is_flaggable(elt.value):
                    self._emit(lineno, kind_name, label, elt.value)

    # ── Comparisons ──────────────────────────────────────────────────────

    def visit_Compare(self, node: ast.Compare) -> None:
        for cmp_node in [node.left, *node.comparators]:
            if isinstance(cmp_node, ast.Constant) and _is_flaggable(cmp_node.value):
                op = type(node.ops[0]).__name__ if node.ops else "?"
                self._emit(node.lineno, "compare", op, cmp_node.value)
        self.generic_visit(node)

    # ── Function calls ───────────────────────────────────────────────────

    def visit_Call(self, node: ast.Call) -> None:
        fn = _call_final_name(node.func)
        if fn not in INDEXER_CALLS:
            for arg in node.args:
                if isinstance(arg, ast.Constant) and _is_flaggable(arg.value):
                    self._emit(node.lineno, "call_pos", f"{fn or '?'}()", arg.value)
        for kw in node.keywords:
            if isinstance(kw.value, ast.Constant) and _is_flaggable(kw.value.value):
                self._emit(node.lineno, "call_kw", f"{fn or '?'}({kw.arg}=)", kw.value.value)
        self.generic_visit(node)

    # ── Function-def defaults ────────────────────────────────────────────

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scan_defaults(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._scan_defaults(node)
        self.generic_visit(node)

    def _scan_defaults(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        args = node.args
        pos_args = (args.args or [])[-len(args.defaults):] if args.defaults else []
        for arg, default in zip(pos_args, args.defaults):
            if isinstance(default, ast.Constant) and _is_flaggable(default.value):
                self._emit(node.lineno, "default", f"{node.name}({arg.arg}=)", default.value)
        for kw_arg, kw_default in zip(args.kwonlyargs, args.kw_defaults):
            if kw_default is None:
                continue
            if isinstance(kw_default, ast.Constant) and _is_flaggable(kw_default.value):
                self._emit(node.lineno, "default", f"{node.name}({kw_arg.arg}=)", kw_default.value)


def scan_source(source: str) -> list[Violation]:
    """Parse Python source and return the list of Violations.

    Returns [] on SyntaxError (cell-mixed Jupyter magic, partial source).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    visitor = HardcodedVisitor()
    visitor.visit(tree)
    return visitor.violations


def format_violation(rel_path: str, v: Violation) -> str:
    return f"{rel_path}:{v.lineno}  [{v.kind}] {v.where} = {v.value}"

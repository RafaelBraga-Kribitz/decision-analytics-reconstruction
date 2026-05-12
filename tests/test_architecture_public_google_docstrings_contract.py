"""Contract: public functions in Module A/B ``src`` use Google/NumPy docstring sections.

Mirrors ``Project_Action_list.md`` Section 4 (code quality): description plus
``Args``/``Parameters``, ``Returns``, ``Raises``, and ``Example``/``Examples``.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_DOCSTRING_SCAN_ROOTS = (
    REPO_ROOT / "module_a_population_segmentation" / "src",
    REPO_ROOT / "module_b_resource_allocation" / "src",
)


def _is_public_api_name(name: str) -> bool:
    if name.startswith("__") and name.endswith("__"):
        return name in {"__init__", "__call__"}
    return not name.startswith("_")


def _is_typing_overload(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "overload":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == "overload":
            return True
    return False


_SECTION_ARGS = re.compile(r"(?m)(?:^Args\s*:)|(?:^Parameters\s*$)")
_SECTION_RETURNS = re.compile(r"(?m)(?:^Returns\s*(?:$|:))|(?:^Yields\s*(?:$|:))")
_SECTION_RAISES = re.compile(r"(?m)^Raises\s*(?:$|:)")
_SECTION_EXAMPLE = re.compile(r"(?m)(?:^Example\s*:)|(?:^Examples\s*$)")


def _google_or_numpy_doc_complete(doc: str | None) -> bool:
    if doc is None or not doc.strip():
        return False
    lines = doc.splitlines()
    if not lines or not lines[0].strip():
        return False
    has_args = bool(_SECTION_ARGS.search(doc))
    has_returns = bool(_SECTION_RETURNS.search(doc))
    has_raises = bool(_SECTION_RAISES.search(doc))
    has_example = bool(_SECTION_EXAMPLE.search(doc))
    return bool(has_args and has_returns and has_raises and has_example)


def _iter_violations() -> list[tuple[str, int, str, str]]:
    """Return ``(relative_path, lineno, qual_name, reason)`` for each violation."""
    violations: list[tuple[str, int, str, str]] = []

    def walk_file(path: Path) -> None:
        rel = str(path.relative_to(REPO_ROOT))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        class_stack: list[str] = []
        func_depth = 0

        def qual_name(fn: str) -> str:
            if class_stack:
                return f"{'.'.join(class_stack)}.{fn}"
            return fn

        def visit_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            nonlocal func_depth
            if func_depth > 0:
                func_depth += 1
                for child in ast.iter_child_nodes(node):
                    dispatch(child)
                func_depth -= 1
                return
            if not _is_public_api_name(node.name):
                func_depth += 1
                for child in ast.iter_child_nodes(node):
                    dispatch(child)
                func_depth -= 1
                return
            if _is_typing_overload(node):
                func_depth += 1
                for child in ast.iter_child_nodes(node):
                    dispatch(child)
                func_depth -= 1
                return
            doc = ast.get_docstring(node)
            if not _google_or_numpy_doc_complete(doc):
                reason = "missing_or_incomplete_docstring_sections"
                if doc and doc.strip():
                    lines = doc.splitlines()
                    if not lines[0].strip():
                        reason = "empty_summary_line"
                    elif not _SECTION_ARGS.search(doc):
                        reason = "missing_args_or_parameters_section"
                    elif not _SECTION_RETURNS.search(doc):
                        reason = "missing_returns_or_yields_section"
                    elif not _SECTION_RAISES.search(doc):
                        reason = "missing_raises_section"
                    elif not _SECTION_EXAMPLE.search(doc):
                        reason = "missing_example_section"
                violations.append((rel, node.lineno, qual_name(node.name), reason))
            func_depth += 1
            for child in ast.iter_child_nodes(node):
                dispatch(child)
            func_depth -= 1

        def dispatch(node: ast.AST) -> None:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit_function(node)
            elif isinstance(node, ast.ClassDef):
                class_stack.append(node.name)
                for child in ast.iter_child_nodes(node):
                    dispatch(child)
                class_stack.pop()
            else:
                for child in ast.iter_child_nodes(node):
                    dispatch(child)

        for child in tree.body:
            dispatch(child)

    for root in _DOCSTRING_SCAN_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            walk_file(path)
    return violations


def test_public_functions_have_google_or_numpy_docstring_sections() -> None:
    violations = _iter_violations()
    if violations:
        sample = "\n".join(f"  {v[0]}:{v[1]} {v[2]} ({v[3]})" for v in violations[:30])
        extra = "" if len(violations) <= 30 else f"\n  ... and {len(violations) - 30} more"
        msg = (
            f"{len(violations)} public API items lack required docstring sections:\n"
            f"{sample}{extra}"
        )
        raise AssertionError(msg)

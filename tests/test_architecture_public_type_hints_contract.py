"""Contract: public functions in Module A/B/C ``src`` have complete annotations.

Maps ``Project_Action_list.md`` Section 4: every parameter and return is typed;
``Any`` must appear with a same-line ``#`` justification (narrow escape hatch).
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_TYPE_HINT_SCAN_ROOTS = (
    REPO_ROOT / "module_a_population_segmentation" / "src",
    REPO_ROOT / "module_b_resource_allocation" / "src",
    REPO_ROOT / "module_c_forecasting_scenarios" / "src",
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


def _annotation_contains_any(node: ast.expr | None) -> bool:
    if node is None:
        return False
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id == "Any":
            return True
    return False


def _line_has_justification_comment(source: str, lineno: int) -> bool:
    line = source.splitlines()[lineno - 1]
    return "#" in line


def _iter_annotation_violations() -> list[tuple[str, int, str, str]]:
    """Missing parameter or return annotations on public API."""
    violations: list[tuple[str, int, str, str]] = []

    def walk_file(path: Path) -> None:
        rel = str(path.relative_to(REPO_ROOT))
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=rel)
        class_stack: list[str] = []
        func_depth = 0

        def qual_name(fn: str) -> str:
            if class_stack:
                return f"{'.'.join(class_stack)}.{fn}"
            return fn

        def skip_self_cls(i: int, names: list[str]) -> bool:
            if not class_stack:
                return False
            return i < len(names) and names[i] in {"self", "cls"}

        def check_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            args = node.args
            all_args: list[tuple[str, ast.expr | None]] = []
            for a in args.posonlyargs + args.args + args.kwonlyargs:
                all_args.append((a.arg, a.annotation))
            if args.vararg is not None:
                all_args.append((args.vararg.arg, args.vararg.annotation))
            if args.kwarg is not None:
                all_args.append((args.kwarg.arg, args.kwarg.annotation))

            names = [n for n, _ in all_args]
            for i, (name, ann) in enumerate(all_args):
                if skip_self_cls(i, names):
                    continue
                if ann is None:
                    violations.append(
                        (
                            rel,
                            node.lineno,
                            qual_name(node.name),
                            f"missing_annotation_param:{name}",
                        )
                    )

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

            check_params(node)
            if node.returns is None:
                # Public API requires an explicit return type (use ``-> None``).
                violations.append(
                    (rel, node.lineno, qual_name(node.name), "missing_return_annotation")
                )

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

    for root in _TYPE_HINT_SCAN_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            walk_file(path)
    return violations


def _iter_any_without_justification() -> list[tuple[str, int, str, str]]:
    """Token-based: a ``def`` line (or continuation) uses ``Any`` without ``#`` on that line."""
    violations: list[tuple[str, int, str, str]] = []

    for root in _TYPE_HINT_SCAN_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = str(path.relative_to(REPO_ROOT))
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=rel)
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

                has_any_in_sig = node.returns is not None and _annotation_contains_any(node.returns)
                args = node.args
                for a in args.posonlyargs + args.args + args.kwonlyargs:
                    if a.annotation and _annotation_contains_any(a.annotation):
                        has_any_in_sig = True
                        break
                if args.vararg and args.vararg.annotation:
                    if _annotation_contains_any(args.vararg.annotation):
                        has_any_in_sig = True
                if args.kwarg and args.kwarg.annotation:
                    if _annotation_contains_any(args.kwarg.annotation):
                        has_any_in_sig = True

                if has_any_in_sig:
                    end = getattr(node, "end_lineno", None) or node.lineno
                    justified = False
                    for ln in range(node.lineno, end + 1):
                        if _line_has_justification_comment(text, ln):
                            justified = True
                            break
                    if not justified:
                        violations.append(
                            (
                                rel,
                                node.lineno,
                                qual_name(node.name),
                                "Any_in_signature_requires_same_block_comment",
                            )
                        )

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

    return violations


def test_public_functions_have_complete_type_annotations() -> None:
    violations = _iter_annotation_violations()
    if violations:
        sample = "\n".join(f"  {v[0]}:{v[1]} {v[2]} ({v[3]})" for v in violations[:40])
        extra = "" if len(violations) <= 40 else f"\n  ... and {len(violations) - 40} more"
        raise AssertionError(
            f"{len(violations)} public API items lack complete annotations:\n{sample}{extra}"
        )


def test_public_functions_any_has_justification_comment() -> None:
    violations = _iter_any_without_justification()
    if violations:
        sample = "\n".join(f"  {v[0]}:{v[1]} {v[2]} ({v[3]})" for v in violations)
        raise AssertionError(
            f"{len(violations)} public API signatures use Any without inline justification:\n"
            f"{sample}"
        )

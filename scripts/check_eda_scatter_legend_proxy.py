#!/usr/bin/env python3
"""Regression guard for issue #124: scatter legends sized from array bubble ``s``.

Matplotlib sizes legend swatches from the largest bubble when ``ax.legend()`` is
called on a labeled scatter whose ``s`` argument is an array. B5/S5 must use
``_region_legend_handles()`` proxy markers instead.

Run: poetry run python scripts/check_eda_scatter_legend_proxy.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"

CHART_HEADER = re.compile(
    r'@safe_chart\("(?P<chart_id>[^"]+)"\)\s*\n'
    r"def (?P<func_name>chart_\w+)\(\):",
)

# ``s=`` values that are plain numeric literals (scalar bubble size).
_SCALAR_S = re.compile(r"^\s*\d+(?:\.\d+)?(?:e[+-]?\d+)?\s*$", re.I)

REQUIRED_PROXY = {
    "chart_b5": "B5",
    "chart_s5": "S5",
}


def _balanced_call(text: str, start: int) -> str:
    """Return the substring ``text[start:]`` through the matching close paren."""
    if start >= len(text) or text[start] != "(":
        return text[start : start + 1]
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def _call_args(call: str) -> str:
    """Inner argument list of a parenthesised call (without outer parens)."""
    inner = call.strip()
    if inner.startswith("(") and inner.endswith(")"):
        return inner[1:-1]
    return inner


def _kw_value(args: str, name: str) -> str | None:
    """Best-effort extraction of a keyword argument value from a call arg string."""
    m = re.search(rf"\b{name}\s*=\s*", args)
    if not m:
        return None
    pos = m.end()
    rest = args[pos:].lstrip()
    if not rest:
        return ""
    if rest[0] in "\"'":
        quote = rest[0]
        end = rest.find(quote, 1)
        return rest[: end + 1] if end != -1 else rest
    depth_paren = depth_bracket = 0
    for i, ch in enumerate(rest):
        if ch == "(":
            depth_paren += 1
        elif ch == ")":
            if depth_paren == 0:
                return rest[:i].rstrip().rstrip(",")
            depth_paren -= 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]":
            depth_bracket -= 1
        elif ch == "," and depth_paren == 0 and depth_bracket == 0:
            return rest[:i].rstrip()
    return rest.rstrip().rstrip(",")


def _is_array_sized(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    if _SCALAR_S.match(value):
        return False
    return True


def _scatter_calls(block: str) -> list[str]:
    calls: list[str] = []
    for m in re.finditer(r"\.scatter\(", block):
        calls.append(_balanced_call(block, m.end() - 1))
    return calls


def _legend_calls(block: str) -> list[str]:
    calls: list[str] = []
    for m in re.finditer(r"ax\.legend\(", block):
        calls.append(_balanced_call(block, m.end() - 1))
    return calls


def _chart_has_regression(block: str) -> bool:
    labeled_array_scatter = False
    for call in _scatter_calls(block):
        args = _call_args(call)
        s_val = _kw_value(args, "s")
        label_val = _kw_value(args, "label")
        if s_val is not None and label_val is not None and _is_array_sized(s_val):
            labeled_array_scatter = True
            break

    if not labeled_array_scatter:
        return False

    for call in _legend_calls(block):
        args = _call_args(call)
        if _kw_value(args, "handles") is None:
            return True
    return False


def _extract_chart_blocks(src: str) -> list[tuple[str, str, str]]:
    markers = list(CHART_HEADER.finditer(src))
    blocks: list[tuple[str, str, str]] = []
    for i, m in enumerate(markers):
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(src)
        body = src[start:end]
        # Drop the trailing ``chart_foo()`` invocation after the function body.
        body = re.split(r"\nchart_\w+\(\)\s*\n", body, maxsplit=1)[0]
        blocks.append((m.group("chart_id"), m.group("func_name"), body))
    return blocks


def main() -> int:
    gaps: list[str] = []

    if not GENERATOR.is_file():
        gaps.append(f"missing generator {GENERATOR.relative_to(REPO_ROOT)}")
    else:
        src = GENERATOR.read_text(encoding="utf-8")
        blocks = _extract_chart_blocks(src)

        for func_name, chart_label in REQUIRED_PROXY.items():
            match = next((b for b in blocks if b[1] == func_name), None)
            if match is None:
                gaps.append(f"missing chart function {func_name}")
            elif "_region_legend_handles(" not in match[2]:
                gaps.append(
                    f"{chart_label} ({func_name}) must call _region_legend_handles() "
                    "for fixed-size legend markers (#124)"
                )

        for chart_id, func_name, body in blocks:
            if _chart_has_regression(body):
                gaps.append(
                    f"{chart_id} ({func_name}): labeled scatter with array ``s`` "
                    "uses ax.legend() without handles= — legend swatch will size from "
                    "the largest bubble (#124)"
                )

    if gaps:
        print("[FAIL] check_eda_scatter_legend_proxy.py: " + "; ".join(gaps), file=sys.stderr)
        return 1

    print(
        "[PASS] check_eda_scatter_legend_proxy.py: bubble scatters use proxy legend "
        "handles where required; no labeled array-s auto-legend regressions"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

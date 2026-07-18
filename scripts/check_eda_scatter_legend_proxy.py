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
    r'@safe_chart\("(?P<chart_id>[^"]+)"\)\s*\n' r"def (?P<func_name>chart_\w+)\(\):",
)

# Plain numeric ``s=`` (scalar bubble). Anything else is treated as array-sized.
_SCALAR_S = re.compile(r"^\d+(?:\.\d+)?$")

REQUIRED_PROXY = {
    "chart_b5": "B5",
    "chart_s5": "S5",
}


def _slice_to_matching_paren(text: str, open_idx: int) -> str:
    """Return text[open_idx:] through the matching ``)`` (open_idx points at ``(``)."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx : i + 1]
    return text[open_idx:]


def _iter_calls(block: str, method: str) -> list[str]:
    """Return argument strings (including parens) for each ``.<method>(...)`` call."""
    needle = f".{method}("
    out: list[str] = []
    start = 0
    while True:
        idx = block.find(needle, start)
        if idx < 0:
            break
        open_idx = idx + len(needle) - 1
        out.append(_slice_to_matching_paren(block, open_idx))
        start = open_idx + 1
    return out


def _kw_simple(args: str, name: str) -> str | None:
    """Extract a simple keyword value (stops at top-level comma)."""
    m = re.search(rf"\b{name}\s*=\s*", args)
    if not m:
        return None
    rest = args[m.end() :]
    depth = 0
    for i, ch in enumerate(rest):
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                return rest[:i].strip().rstrip(",")
            depth -= 1
        elif ch == "," and depth == 0:
            return rest[:i].strip()
    return rest.strip().rstrip(",")


def _is_array_sized(value: str) -> bool:
    value = value.strip()
    return bool(value) and not _SCALAR_S.match(value)


def _chart_has_regression(block: str) -> bool:
    labeled_array = any(
        _is_array_sized(_kw_simple(call, "s") or "") and _kw_simple(call, "label") is not None
        for call in _iter_calls(block, "scatter")
    )
    if not labeled_array:
        return False
    return any(_kw_simple(call, "handles") is None for call in _iter_calls(block, "legend"))


def _extract_chart_blocks(src: str) -> list[tuple[str, str, str]]:
    markers = list(CHART_HEADER.finditer(src))
    blocks: list[tuple[str, str, str]] = []
    for i, m in enumerate(markers):
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(src)
        body = re.split(r"\nchart_\w+\(\)\s*\n", src[start:end], maxsplit=1)[0]
        blocks.append((m.group("chart_id"), m.group("func_name"), body))
    return blocks


def _check_required_proxies(blocks: list[tuple[str, str, str]]) -> list[str]:
    gaps: list[str] = []
    for func_name, chart_label in REQUIRED_PROXY.items():
        match = next((b for b in blocks if b[1] == func_name), None)
        if match is None:
            gaps.append(f"missing chart function {func_name}")
        elif "_region_legend_handles(" not in match[2]:
            gaps.append(
                f"{chart_label} ({func_name}) must call _region_legend_handles() "
                "for fixed-size legend markers (#124)"
            )
    return gaps


def _check_regressions(blocks: list[tuple[str, str, str]]) -> list[str]:
    gaps: list[str] = []
    for chart_id, func_name, body in blocks:
        if _chart_has_regression(body):
            gaps.append(
                f"{chart_id} ({func_name}): labeled scatter with array ``s`` "
                "uses ax.legend() without handles= — legend swatch will size from "
                "the largest bubble (#124)"
            )
    return gaps


def main() -> int:
    if not GENERATOR.is_file():
        print(
            f"[FAIL] check_eda_scatter_legend_proxy.py: missing generator "
            f"{GENERATOR.relative_to(REPO_ROOT)}",
            file=sys.stderr,
        )
        return 1

    blocks = _extract_chart_blocks(GENERATOR.read_text(encoding="utf-8"))
    gaps = _check_required_proxies(blocks) + _check_regressions(blocks)
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

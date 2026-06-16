"""Detect hardcoded magic values in SQL source files.

Scans *.sql and *.sql.j2 under sql/, queries/, models/, notebooks/, scripts/,
src/. Regex-based — SQL has no clean stdlib AST.

Flags:
  - integer literals >= 10 (likely thresholds, not indices)
  - date literals 'YYYY-MM-DD'
  - INTERVAL '<n> <unit>' literals

Allowlist:
  - integers inside LIMIT / OFFSET / FETCH FIRST clauses (pagination)
  - anything inside -- line comments or /* block comments */

Gate: F-SQL-HARDCODED-VALUES (sql_drift category)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

SCAN_DIRS = ["sql", "queries", "models", "notebooks", "scripts", "src"]
EXCLUDE_DIRS = {".venv", "venv", "__pycache__", ".git"}
EXTS = ("*.sql", "*.sql.j2")

_FINDING_ID = "F-SQL-HARDCODED-VALUES"
_SCRIPT_NAME = "check_sql_values.py"

LINE_COMMENT_RE = re.compile(r"--[^\n]*")
BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
PAGINATION_RE = re.compile(
    r"\b(LIMIT|OFFSET|FETCH\s+FIRST|FETCH\s+NEXT)\s+\d+",
    re.IGNORECASE,
)

INT_RE = re.compile(r"\b\d{2,}\b")
DATE_RE = re.compile(r"'(\d{4}-\d{2}-\d{2})'")
INTERVAL_RE = re.compile(
    r"INTERVAL\s+'(\d+\s+(?:day|days|month|months|year|years|hour|hours|minute|minutes))'",
    re.IGNORECASE,
)


def _strip_safe(line: str) -> str:
    s = LINE_COMMENT_RE.sub("", line)
    s = PAGINATION_RE.sub("", s)
    return s


def _scan_sql(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    text = BLOCK_COMMENT_RE.sub("", text)
    rel = str(path.relative_to(REPO_ROOT))
    out: list[str] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = _strip_safe(raw)
        for m in INT_RE.finditer(line):
            out.append(f"{rel}:{lineno}  [sql_int] {m.group(0)}")
        for m in DATE_RE.finditer(line):
            out.append(f"{rel}:{lineno}  [sql_date] {m.group(1)}")
        for m in INTERVAL_RE.finditer(line):
            out.append(f"{rel}:{lineno}  [sql_interval] {m.group(1)}")
    return out


def _sql_files_to_scan() -> list[Path]:
    files: list[Path] = []
    for dirname in SCAN_DIRS:
        d = REPO_ROOT / dirname
        if not d.exists():
            continue
        for ext in EXTS:
            for f in d.rglob(ext):
                if any(part in EXCLUDE_DIRS for part in f.parts):
                    continue
                files.append(f)
    for ext in EXTS:
        for f in REPO_ROOT.glob(ext):
            files.append(f)
    return files


def main() -> int:
    files = _sql_files_to_scan()
    if not files:
        print(f"[SKIP] {_SCRIPT_NAME}: no .sql files found")
        return 0

    all_violations: list[str] = []
    for f in files:
        all_violations.extend(_scan_sql(f))

    if all_violations:
        return gate(
            _FINDING_ID,
            _SCRIPT_NAME,
            False,
            f"{len(all_violations)} hardcoded value(s) in SQL. First: {all_violations[0]}",
        )
    return gate(_FINDING_ID, _SCRIPT_NAME, True, "no hardcoded values in SQL")


if __name__ == "__main__":
    sys.exit(main())

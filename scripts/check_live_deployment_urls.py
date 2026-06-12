#!/usr/bin/env python3
"""Verify public deployment URLs are live before portfolio publication."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from _governance_check import gate

# Render free tier cold-starts can exceed 45s; health path + retries reduce flakes.
ENDPOINTS: dict[str, dict[str, object]] = {
    "module_a_streamlit": {
        "url": "https://decision-analytics-module-a.onrender.com/_stcore/health",
        "timeout": 90,
        "attempts": 2,
    },
    "module_b_fastapi_docs": {
        "url": "https://decision-analytics-module-b-production.up.railway.app/docs",
        "timeout": 30,
        "attempts": 1,
    },
    "module_c_quarto": {
        "url": "https://RafaelBraga-Kribitz.github.io/decision-analytics-reconstruction/",
        "timeout": 30,
        "attempts": 1,
    },
}


def _status_once(url: str, timeout: int) -> int | str:
    req = Request(url, headers={"User-Agent": "decision-analytics-governance-check/1.0"})
    try:
        with urlopen(req, timeout=timeout) as response:  # noqa: S310 - fixed public URLs.
            return int(response.status)
    except HTTPError as exc:
        return int(exc.code)
    except URLError as exc:
        return exc.reason.__class__.__name__
    except TimeoutError:
        return "Timeout"


def _status(name: str, config: dict[str, object]) -> int | str:
    url = str(config["url"])
    timeout = int(config["timeout"])
    attempts = int(config["attempts"])
    last: int | str = "Timeout"
    for _ in range(attempts):
        last = _status_once(url, timeout)
        if last == 200:
            return last
    return last


def main() -> int:
    statuses = {name: _status(name, config) for name, config in ENDPOINTS.items()}
    ok = all(status == 200 for status in statuses.values())
    detail = ", ".join(f"{name}={status}" for name, status in statuses.items())
    return gate("F-021", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())

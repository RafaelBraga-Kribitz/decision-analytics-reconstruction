#!/usr/bin/env python3
"""Verify public deployment URLs are live before portfolio publication."""

from __future__ import annotations

import time
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from _governance_check import gate

URLS = {
    "module_a_streamlit": "https://decision-analytics-module-a.onrender.com",
    "module_b_fastapi_docs": "https://decision-analytics-module-b-production.up.railway.app/docs",
    "module_c_quarto": "https://RafaelBraga-Kribitz.github.io/decision-analytics-reconstruction/",
}

# Render free tier cold-starts take up to ~50 s; allow one retry after a wake delay.
_TIMEOUT = 90
_RENDER_RETRY_DELAY = 20


def _fetch(url: str) -> int | str:
    req = Request(url, headers={"User-Agent": "decision-analytics-governance-check/1.0"})
    try:
        with urlopen(req, timeout=_TIMEOUT) as response:
            return int(response.status)
    except HTTPError as exc:
        return int(exc.code)
    except URLError as exc:
        return exc.reason.__class__.__name__
    except TimeoutError:
        return "Timeout"


def _status(name: str, url: str) -> int | str:
    result = _fetch(url)
    # One retry for Render — the first request wakes the dyno; the second lands warm.
    if result != 200 and "render.com" in url:
        time.sleep(_RENDER_RETRY_DELAY)
        result = _fetch(url)
    return result


def main() -> int:
    statuses = {name: _status(name, url) for name, url in URLS.items()}
    ok = all(status == 200 for status in statuses.values())
    detail = ", ".join(f"{name}={status}" for name, status in statuses.items())
    return gate("F-021", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())

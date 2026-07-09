#!/usr/bin/env python3
"""Verify public deployment URLs are live before portfolio publication.

Sandboxed runners (issue #41) can't reach the public internet, so an operator
may set ``GOVERNANCE_NETWORK_CHECKS=skip`` to skip with an explicit [SKIP]
marker. CI leaves the variable unset and enforces the check.
"""

from __future__ import annotations

import os
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

_MAX_RETRIES = 3
_BACKOFF_BASE = 2


def _is_timeout(exc: URLError) -> bool:
    reason = exc.reason.__class__.__name__
    return reason == "ConnectTimeoutError" or "timeout" in str(exc.reason).lower()


def _status(url: str) -> int | str:
    req = Request(url, headers={"User-Agent": "decision-analytics-governance-check/1.0"})
    for attempt in range(_MAX_RETRIES):
        try:
            with urlopen(req, timeout=15) as response:
                return int(response.status)
        except HTTPError as exc:
            return int(exc.code)
        except URLError as exc:
            if _is_timeout(exc) and attempt < _MAX_RETRIES - 1:
                time.sleep(_BACKOFF_BASE**attempt)
                continue
            return exc.reason.__class__.__name__
        except TimeoutError:
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_BACKOFF_BASE**attempt)
                continue
            return "Timeout"
    return "Timeout"


def main() -> int:
    if os.environ.get("GOVERNANCE_NETWORK_CHECKS") == "skip":
        print(
            "[SKIP] check_live_deployment_urls.py: F-021 network checks skipped "
            "(GOVERNANCE_NETWORK_CHECKS=skip — sandboxed runner)"
        )
        return 0
    statuses = {name: _status(url) for name, url in URLS.items()}
    ok = all(status == 200 for status in statuses.values())
    detail = ", ".join(f"{name}={status}" for name, status in statuses.items())
    return gate("F-021", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())

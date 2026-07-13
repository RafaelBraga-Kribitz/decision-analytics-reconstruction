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

# Retry delays sized to outlast a full Render free-tier cold start (~60-120 s
# observed; the old 2s/4s/8s ≈ 14 s window caused recurrences 1-3). Total wait
# ≈ 245 s plus per-request timeouts. A keep-alive workflow
# (.github/workflows/keepalive.yml) additionally pings Module A every 10 min
# so the probe rarely sees a cold instance at all.
_RETRY_DELAYS = (5, 10, 20, 40, 80, 90)
_MAX_RETRIES = len(_RETRY_DELAYS) + 1


def _is_timeout(exc: URLError) -> bool:
    reason = exc.reason.__class__.__name__
    return reason == "ConnectTimeoutError" or "timeout" in str(exc.reason).lower()


def _status(url: str) -> int | str:
    req = Request(url, headers={"User-Agent": "decision-analytics-governance-check/1.0"})
    for attempt in range(_MAX_RETRIES):
        try:
            with urlopen(req, timeout=30) as response:
                return int(response.status)
        except HTTPError as exc:
            # 502/503/504 while a free-tier instance boots deserves a retry too.
            if exc.code in (502, 503, 504) and attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAYS[attempt])
                continue
            return int(exc.code)
        except URLError as exc:
            if _is_timeout(exc) and attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAYS[attempt])
                continue
            return exc.reason.__class__.__name__
        except TimeoutError:
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAYS[attempt])
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

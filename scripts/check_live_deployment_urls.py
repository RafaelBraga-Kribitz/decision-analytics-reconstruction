#!/usr/bin/env python3
"""Verify public deployment URLs are live before portfolio publication."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from _governance_check import gate

URLS = {
    "module_a_streamlit": "https://decision-analytics-module-a.onrender.com",
    "module_b_fastapi_docs": "https://decision-analytics-module-b-production.up.railway.app/docs",
    "module_c_quarto": "https://RafaelBraga-Kribitz.github.io/decision-analytics-reconstruction/",
}


def _status(url: str) -> int | str:
    """Check URL status with retry logic for free-tier service spinup.

    Render free tier sleeps after 15 min idle; first request may timeout.
    Retry up to 3 times with backoff to allow spinup.
    """
    import time

    req = Request(url, headers={"User-Agent": "decision-analytics-governance-check/1.0"})
    max_retries = 3
    backoff_base = 2

    for attempt in range(max_retries):
        try:
            with urlopen(req, timeout=15) as response:
                return int(response.status)
        except HTTPError as exc:
            return int(exc.code)
        except URLError as exc:
            reason = exc.reason.__class__.__name__
            if reason == "ConnectTimeoutError" or "timeout" in str(exc.reason).lower():
                if attempt < max_retries - 1:
                    delay = backoff_base ** attempt
                    time.sleep(delay)
                    continue
            return reason
        except TimeoutError:
            if attempt < max_retries - 1:
                delay = backoff_base ** attempt
                time.sleep(delay)
                continue
            return "Timeout"

    return "Timeout"


def main() -> int:
    statuses = {name: _status(url) for name, url in URLS.items()}
    ok = all(status == 200 for status in statuses.values())
    detail = ", ".join(f"{name}={status}" for name, status in statuses.items())
    return gate("F-021", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())

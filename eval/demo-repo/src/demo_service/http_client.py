"""Outbound HTTP."""

import urllib.request


def fetch_status(url: str) -> int:
    with urllib.request.urlopen(url, timeout=10) as response:
        return int(response.status)

"""Quarantine list lookup."""

from __future__ import annotations


def fetch_quarantine_list() -> list[str]:
    """Return the node IDs currently quarantined for this repository.

    Not implemented: this always returns an empty list, so no test is ever
    quarantined.
    """
    return []

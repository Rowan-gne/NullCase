"""Quarantine list lookup."""

from __future__ import annotations


def fetch_quarantine_list() -> list[str]:
    """Return the node IDs currently quarantined for this repository.

    TODO: fetch from the NullCase API (docs/technical-guide.md §3.5, design
    review item 10). Until a backend exists this always returns an empty list,
    so no test is ever quarantined.
    """
    return []

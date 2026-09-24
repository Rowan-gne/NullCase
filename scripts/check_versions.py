"""Check that every published package, and the action's pinned plugin, share one version.

Usage: python scripts/check_versions.py [EXPECTED]
With EXPECTED (e.g. from a v0.1.0 tag, minus the "v"), versions must equal it.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("packages/pytest-plugin", "packages/retrieval", "sandbox")
ACTION = ROOT / "packages/upload-action/action.yml"


def versions() -> dict[str, str]:
    found: dict[str, str] = {}
    for package in PACKAGES:
        project = tomllib.loads((ROOT / package / "pyproject.toml").read_text())["project"]
        found[project["name"]] = project["version"]
    pin = re.search(r"nullcase-pytest==([0-9][^'\"\s]*)", ACTION.read_text())
    found["upload-action plugin pin"] = pin.group(1) if pin else "<missing>"
    return found


def main(argv: list[str]) -> int:
    found = versions()
    expected = argv[1] if len(argv) > 1 else next(iter(found.values()))
    mismatched = {name: v for name, v in found.items() if v != expected}
    for name, version in found.items():
        print(f"{name}: {version}")
    if mismatched:
        print(f"error: expected {expected} everywhere", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

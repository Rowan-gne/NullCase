"""``nullcase-coverage [--project DIR] NODEID FILE LINES``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nullcase_sandbox.battery import BatteryError
from nullcase_sandbox.coverage_check import check_coverage, parse_lines


def _fmt(lines: frozenset[int]) -> str:
    return ", ".join(map(str, sorted(lines))) or "-"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nullcase-coverage",
        description="Report whether one test executes the given lines of a file.",
    )
    parser.add_argument("nodeid", help="test node ID, relative to the project's pytest rootdir")
    parser.add_argument("file", type=Path, help="target file, relative to the project")
    parser.add_argument("lines", type=parse_lines, help='line numbers, e.g. "3,5-8"')
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="default: cwd")
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args(argv)

    try:
        result = check_coverage(args.project, args.nodeid, args.file, args.lines, args.python)
    except BatteryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"test: {result.nodeid} ({result.test_outcome})")
    print(f"file: {result.target_file}")
    print(f"covered:        {_fmt(result.covered)}")
    print(f"not covered:    {_fmt(result.missed)}")
    print(f"not executable: {_fmt(result.not_executable)}")
    print("result: all requested lines covered" if result.all_covered else "result: NOT covered")
    return 0 if result.all_covered else 1


if __name__ == "__main__":
    raise SystemExit(main())

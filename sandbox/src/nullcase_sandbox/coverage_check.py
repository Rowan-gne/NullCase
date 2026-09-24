"""Coverage check for one test (docs/technical-guide.md §3.7, last battery row).

Runs a single test under coverage.py, measuring only the target file, and
reports which of the requested lines it executed. This is the check meant to
confirm that a generated test exercises the code it was written for.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from nullcase_sandbox.battery import COMMON_ARGS, NO_SHUFFLE, PINNED_ENV, BatteryError


@dataclass(frozen=True, slots=True)
class CoverageResult:
    nodeid: str
    target_file: Path
    test_outcome: str
    covered: frozenset[int]
    missed: frozenset[int]
    # Requested lines coverage.py doesn't consider executable (blank, comments, docstrings).
    not_executable: frozenset[int]

    @property
    def all_covered(self) -> bool:
        return not self.missed


def parse_lines(spec: str) -> frozenset[int]:
    """Parse ``"3,5-8"`` into ``{3, 5, 6, 7, 8}``."""
    lines: set[int] = set()
    for part in filter(None, (p.strip() for p in spec.split(","))):
        start, _, end = part.partition("-")
        first, last = int(start), int(end or start)
        if first < 1 or last < first:
            raise ValueError(f"invalid line range: {part!r}")
        lines.update(range(first, last + 1))
    return frozenset(lines)


def check_coverage(
    project: Path,
    nodeid: str,
    target_file: Path,
    lines: Iterable[int],
    python: str,
    timeout_s: float = 120.0,
) -> CoverageResult:
    project = project.resolve()
    target = (project / target_file).resolve()
    if not target.is_file():
        raise BatteryError(f"target file not found: {target}")
    requested = frozenset(lines)

    with tempfile.TemporaryDirectory(prefix="nullcase-cov-") as tmp:
        data = Path(tmp) / ".coverage"
        report = Path(tmp) / "coverage.json"
        results = Path(tmp) / "results.jsonl"
        env = {**os.environ, **PINNED_ENV}
        coverage = [python, "-m", "coverage"]
        subprocess.run(
            [
                *coverage,
                "run",
                f"--data-file={data}",
                f"--include={target}",
                "-m",
                "pytest",
                *COMMON_ARGS,
                *NO_SHUFFLE,
                f"--nullcase-results={results}",
                nodeid,
            ],
            cwd=project,
            env=env,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
        outcome = _test_outcome(results, nodeid)
        if outcome is None:
            raise BatteryError(f"{nodeid!r} did not run; check the node ID and the project")
        json_run = subprocess.run(
            [*coverage, "json", f"--data-file={data}", "-o", str(report)],
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        executed: set[int] = set()
        missing: set[int] = set()
        # "No data to report" (exit 1, no file) means the target was never imported.
        if report.exists():
            for name, entry in json.loads(report.read_text(encoding="utf-8"))["files"].items():
                if (project / name).resolve() == target:
                    executed = set(entry["executed_lines"])
                    missing = set(entry["missing_lines"])
        elif "No data to report" not in json_run.stdout + json_run.stderr:
            raise BatteryError(f"coverage json failed: {json_run.stderr.strip()}")

    if not executed and not missing:
        # Target never imported: every executable line is unknown to coverage, so
        # treat all requested lines as missed rather than silently "not executable".
        return CoverageResult(nodeid, target, outcome, frozenset(), requested, frozenset())
    return CoverageResult(
        nodeid,
        target,
        outcome,
        covered=requested & frozenset(executed),
        missed=requested & frozenset(missing),
        not_executable=requested - frozenset(executed) - frozenset(missing),
    )


def _test_outcome(results: Path, nodeid: str) -> str | None:
    if not results.exists():
        return None
    for line in results.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record["nodeid"] == nodeid:
            return str(record["outcome"])
    return None

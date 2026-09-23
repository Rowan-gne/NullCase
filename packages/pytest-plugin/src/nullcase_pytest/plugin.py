"""pytest hooks that fold each test's phases into one ResultRecord.

The plugin is inactive unless ``--nullcase-results PATH`` is given.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from nullcase_pytest.quarantine import fetch_quarantine_list
from nullcase_pytest.results import Outcome, ResultRecord
from nullcase_pytest.sinks import LocalFileSink, ResultsSink

_RESULTS_DEST = "nullcase_results"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("nullcase")
    group.addoption(
        "--nullcase-results",
        dest=_RESULTS_DEST,
        metavar="PATH",
        default=None,
        help="Write one JSON line per test result to PATH.",
    )


def pytest_configure(config: pytest.Config) -> None:
    results_path: str | None = config.getoption(_RESULTS_DEST)
    # Under pytest-xdist, workers forward their reports to the controller,
    # so only the controller records; otherwise every result would be doubled.
    if results_path is None or hasattr(config, "workerinput"):
        return
    path = config.invocation_params.dir / Path(results_path)
    config.pluginmanager.register(ResultRecorder(LocalFileSink(path)), "nullcase-recorder")


@dataclass
class _InProgress:
    file_path: str
    outcome: Outcome | None = None
    duration_s: float = 0.0


class ResultRecorder:
    """Collects phase reports per node ID and emits a record after teardown."""

    def __init__(self, sink: ResultsSink) -> None:
        self._sink = sink
        self._in_progress: dict[str, _InProgress] = {}
        self.quarantined: list[str] = []

    def pytest_sessionstart(self) -> None:
        # TODO: once the quarantine list is real, quarantined failures should
        # be reported but not fail the job (technical guide, design review 10).
        self.quarantined = fetch_quarantine_list()

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        state = self._in_progress.setdefault(report.nodeid, _InProgress(report.location[0]))
        state.duration_s += report.duration
        state.outcome = _merge(state.outcome, phase_outcome(report))
        if report.when == "teardown":
            del self._in_progress[report.nodeid]
            self._sink.write(
                ResultRecord(
                    nodeid=report.nodeid,
                    file_path=state.file_path,
                    outcome=state.outcome or "passed",
                    duration_s=round(state.duration_s, 6),
                )
            )

    def pytest_sessionfinish(self) -> None:
        self._sink.close()


def phase_outcome(report: pytest.TestReport) -> Outcome | None:
    """Outcome implied by a single phase report, or None if it implies nothing."""
    xfail = hasattr(report, "wasxfail")
    if report.when == "call":
        if report.passed:
            return "xpassed" if xfail else "passed"
        if report.skipped:
            return "xfailed" if xfail else "skipped"
        return "failed"
    # setup / teardown
    if report.failed:
        return "error"
    if report.skipped:
        return "xfailed" if xfail else "skipped"
    return None


def _merge(current: Outcome | None, new: Outcome | None) -> Outcome | None:
    if current is None:
        return new
    # A teardown error overrides a clean call, but not a call that already failed.
    if new == "error" and current not in ("failed", "error"):
        return "error"
    return current

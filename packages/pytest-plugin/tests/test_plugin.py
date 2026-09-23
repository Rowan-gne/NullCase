import json
from pathlib import Path
from typing import Any

import pytest

SAMPLE = """
import pytest

def test_pass():
    pass

def test_fail():
    assert 1 == 2

@pytest.mark.skip(reason="no")
def test_skip():
    pass

@pytest.mark.xfail(reason="known")
def test_xfail():
    assert False

@pytest.mark.xfail(reason="known")
def test_xpass():
    pass

@pytest.fixture
def broken_setup():
    raise RuntimeError("setup")

def test_setup_error(broken_setup):
    pass

@pytest.fixture
def broken_teardown():
    yield
    raise RuntimeError("teardown")

def test_teardown_error(broken_teardown):
    pass

@pytest.mark.parametrize("n", [1, 2])
def test_param(n):
    assert n == 1
"""


def read_results(path: Path) -> dict[str, dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    return {r["nodeid"]: r for r in records}


def test_records_every_outcome(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(test_sample=SAMPLE)
    pytester.runpytest("--nullcase-results=out/results.jsonl")

    results = read_results(pytester.path / "out" / "results.jsonl")
    outcomes = {nodeid.split("::")[1]: r["outcome"] for nodeid, r in results.items()}
    assert outcomes == {
        "test_pass": "passed",
        "test_fail": "failed",
        "test_skip": "skipped",
        "test_xfail": "xfailed",
        "test_xpass": "xpassed",
        "test_setup_error": "error",
        "test_teardown_error": "error",
        "test_param[1]": "passed",
        "test_param[2]": "failed",
    }


def test_records_nodeid_file_path_and_duration(pytester: pytest.Pytester) -> None:
    pytester.mkpydir("pkg")
    pytester.path.joinpath("pkg", "test_timed.py").write_text(
        "import time\n\ndef test_slow():\n    time.sleep(0.05)\n", encoding="utf-8"
    )
    pytester.runpytest("--nullcase-results=results.jsonl")

    results = read_results(pytester.path / "results.jsonl")
    record = results["pkg/test_timed.py::test_slow"]
    assert record["file_path"] == "pkg/test_timed.py"
    assert record["outcome"] == "passed"
    assert record["duration_s"] >= 0.05


def test_does_not_change_the_session_result(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(test_sample=SAMPLE)
    result = pytester.runpytest("--nullcase-results=results.jsonl")
    # pytest counts test_teardown_error as both passed (call) and error (teardown).
    result.assert_outcomes(passed=3, failed=2, skipped=1, xfailed=1, xpassed=1, errors=2)


def test_inactive_without_option(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(test_sample="def test_ok():\n    pass\n")
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    assert list(pytester.path.glob("*.jsonl")) == []


def test_xdist_records_each_test_once(pytester: pytest.Pytester) -> None:
    pytest.importorskip("xdist")
    pytester.makepyfile(test_sample=SAMPLE)
    pytester.runpytest_subprocess("-n", "2", "--nullcase-results=results.jsonl")

    lines = (pytester.path / "results.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 9
    assert len(read_results(pytester.path / "results.jsonl")) == 9

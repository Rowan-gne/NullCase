import sys
from pathlib import Path

import pytest
from nullcase_sandbox.battery import BatteryError
from nullcase_sandbox.coverage_check import check_coverage, parse_lines

DEMO_REPO = Path(__file__).resolve().parents[2] / "eval" / "demo-repo"
ORDER_TEST = "tests/test_order.py::test_first_user_gets_id_1"
REGISTRY = Path("src/demo_service/registry.py")


def test_demo_test_covers_register_but_not_count() -> None:
    # registry.py: lines 8-9 are register()'s body, line 13 is count()'s body,
    # line 2 is blank. The test calls register() only.
    result = check_coverage(DEMO_REPO, ORDER_TEST, REGISTRY, {2, 8, 9, 13}, sys.executable)
    assert result.test_outcome == "passed"
    assert result.covered == {8, 9}
    assert result.missed == {13}
    assert result.not_executable == {2}
    assert not result.all_covered


def test_all_covered_when_only_exercised_lines_requested() -> None:
    result = check_coverage(DEMO_REPO, ORDER_TEST, REGISTRY, {8, 9}, sys.executable)
    assert result.all_covered


def test_target_never_imported_reports_every_line_missed() -> None:
    result = check_coverage(
        DEMO_REPO, ORDER_TEST, Path("src/demo_service/tags.py"), {5, 6}, sys.executable
    )
    assert result.covered == frozenset()
    assert result.missed == {5, 6}


def test_unknown_nodeid_is_an_error() -> None:
    with pytest.raises(BatteryError, match="did not run"):
        check_coverage(DEMO_REPO, "tests/test_order.py::nope", REGISTRY, {8}, sys.executable)


def test_parse_lines() -> None:
    assert parse_lines("3, 5-7,3") == {3, 5, 6, 7}
    with pytest.raises(ValueError):
        parse_lines("7-5")

from pathlib import Path

import pytest
from nullcase_sandbox.coverage_cli import main

DEMO_REPO = Path(__file__).resolve().parents[2] / "eval" / "demo-repo"
ORDER_TEST = "tests/test_order.py::test_first_user_gets_id_1"
REGISTRY = "src/demo_service/registry.py"


def run(lines: str) -> list[str]:
    return ["--project", str(DEMO_REPO), ORDER_TEST, REGISTRY, lines]


def test_reports_missed_lines_and_exits_1(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(run("2,8-9,13")) == 1
    out = capsys.readouterr().out
    assert "test: tests/test_order.py::test_first_user_gets_id_1 (passed)" in out
    assert "covered:        8, 9" in out
    assert "not covered:    13" in out
    assert "not executable: 2" in out
    assert "result: NOT covered" in out


def test_exits_0_when_every_requested_line_is_covered(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(run("8-9")) == 0
    assert "result: all requested lines covered" in capsys.readouterr().out


def test_reports_errors_with_exit_code_2(capsys: pytest.CaptureFixture[str]) -> None:
    argv = ["--project", str(DEMO_REPO), ORDER_TEST, "src/demo_service/nope.py", "1"]
    assert main(argv) == 2
    assert "error: target file not found" in capsys.readouterr().err

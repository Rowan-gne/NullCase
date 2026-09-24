import argparse
import json
import subprocess
import sys
from pathlib import Path

import pytest
from nullcase_sandbox.battery import BatteryReport, Target
from nullcase_sandbox.cli import format_report, main, perturbation_list
from nullcase_sandbox.diagnosis import flipped
from nullcase_sandbox.stats import Rate


def test_only_accepts_a_comma_separated_list_in_canonical_order() -> None:
    assert perturbation_list("hash_seed, order") == ["order", "hash_seed"]


@pytest.mark.parametrize("value", ["", "order,bogus", "tests/test_x.py::test_y"])
def test_only_rejects_unknown_names(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        perturbation_list(value)


ORDER_DEPENDENT = """
_seen = []


def test_victim():
    _seen.append("victim")
    assert _seen == ["victim"]


def test_polluter_a():
    _seen.append("a")


def test_polluter_b():
    _seen.append("b")


def test_polluter_c():
    _seen.append("c")
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (tmp_path / "test_state.py").write_text(ORDER_DEPENDENT, encoding="utf-8")
    return tmp_path


def run_cli(project: Path, *extra: str) -> list[str]:
    return [
        "--project",
        str(project),
        "--baseline-runs",
        "15",
        "--runs",
        "15",
        "--only",
        "order",
        *extra,
        "test_state.py::test_victim",
    ]


def test_battery_cli_prints_table_diagnosis_and_repro(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(run_cli(project)) == 0
    out = capsys.readouterr().out
    assert "target: test_state.py::test_victim" in out
    assert "differs from baseline" in out
    assert "diagnosis: order_dependent (wilson interval)" in out
    assert "--randomly-seed=" in out


def test_battery_cli_json_output(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(run_cli(project, "--json")) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["category"] == "order_dependent"
    assert report["method"] == "wilson_interval"
    assert report["baseline"]["runs"] == 15
    assert set(report["perturbations"]) == {"order"}
    assert report["repro"]["confirmed_failures"] == report["repro"]["confirm_runs"] == 3


def test_battery_cli_reports_errors_with_exit_code_2(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["--project", str(project), "--baseline-runs", "2", "test_state.py::missing"]
    assert main(argv) == 2
    assert "error:" in capsys.readouterr().err


def test_format_report_explains_a_deterministic_flip(project: Path) -> None:
    report = BatteryReport(
        target=Target(project, "test_state.py::test_victim", sys.executable),
        baseline=Rate(20, 20),
        perturbations={"hash_seed": Rate(15, 20)},
        diagnosis=flipped("hash_seed", "PYTHONHASHSEED=1"),
        repro=None,
    )
    text = format_report(report)
    assert "diagnosis: hash_order (deterministic flip)" in text
    assert "pinned baseline failed every run; PYTHONHASHSEED=1 passes on every replay" in text
    assert "repro: none found" in text


def test_module_entry_point_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "nullcase_sandbox", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "usage: nullcase-battery" in result.stdout

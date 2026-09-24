import subprocess
import sys
from pathlib import Path

import pytest
from nullcase_sandbox.battery import (
    ORDER_SEEDS,
    PINNED_ENV,
    TIMEZONES,
    BatteryError,
    Target,
    plan,
    run_battery,
)

ORDER_DEPENDENT = """
_registry = []


def register(name):
    _registry.append(name)
    return len(_registry)


def test_first_registration_gets_id_1():
    assert register("victim") == 1


def test_polluter_a():
    register("a")


def test_polluter_b():
    register("b")


def test_polluter_c():
    register("c")
"""

NODEID = "test_registry.py::test_first_registration_gets_id_1"


def test_plan_pins_baseline_and_varies_one_factor_per_perturbation() -> None:
    baseline, perturbations = plan(NODEID, baseline_runs=3, runs=5)
    assert len(baseline) == 3
    assert all(spec.env == PINNED_ENV for spec in baseline)
    assert all("no:randomly" in spec.pytest_args for spec in baseline)
    assert {len(specs) for specs in perturbations.values()} == {5}

    seeds = [spec.env["PYTHONHASHSEED"] for spec in perturbations["hash_seed"]]
    assert seeds == ["1", "2", "3", "4", "5"] and "0" not in seeds
    assert {spec.env["TZ"] for spec in perturbations["timezone"]} == set(TIMEZONES)
    assert all("--disable-socket" in s.pytest_args for s in perturbations["network_off"])
    assert all("test_registry.py" in s.pytest_args for s in perturbations["order"])
    assert [s.pytest_args[0] for s in perturbations["order"]] == [
        f"--randomly-seed={seed}" for seed in ORDER_SEEDS[:5]
    ]
    assert all("-n" in s.pytest_args for s in perturbations["parallel"])


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (tmp_path / "test_registry.py").write_text(ORDER_DEPENDENT, encoding="utf-8")
    return tmp_path


def test_diagnoses_order_dependent_test_with_working_repro(project: Path) -> None:
    target = Target(project, NODEID, sys.executable)
    report = run_battery(target, baseline_runs=15, runs=15, perturbations=["order", "hash_seed"])

    assert report.baseline.failures == 0
    assert report.diagnosis.category == "order_dependent"
    assert report.repro is not None
    assert "--randomly-seed=" in report.repro.command

    replay = subprocess.run(report.repro.command, shell=True, capture_output=True, check=False)
    assert replay.returncode == 1, replay.stdout


def test_unknown_nodeid_is_reported(project: Path) -> None:
    target = Target(project, "test_registry.py::nope", sys.executable)
    with pytest.raises(BatteryError, match="no result"):
        run_battery(target, baseline_runs=2, runs=2, perturbations=["order"])

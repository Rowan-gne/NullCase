import json
import os
import subprocess
import sys
from pathlib import Path

from entrypoint import (
    Diagnosis,
    Settings,
    annotation,
    annotation_file,
    read_settings,
    render_summary,
    select_targets,
)
from nullcase_sandbox.battery import BatteryReport, Repro, Target, plan, repro_command
from nullcase_sandbox.cli import report_to_dict
from nullcase_sandbox.diagnosis import Diagnosis as BatteryDiagnosis
from nullcase_sandbox.stats import Rate

ENTRYPOINT = Path(__file__).resolve().parents[1] / "entrypoint.py"
DIAGNOSE_FIXTURE = Path(__file__).resolve().parents[1] / "standalone" / "self-test-diagnose"

SAMPLE = """
def test_ok():
    pass

def test_bad():
    assert False
"""


def run(project: Path, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ENTRYPOINT)],
        cwd=project,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def make_project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (tmp_path / "test_sample.py").write_text(SAMPLE, encoding="utf-8")
    return tmp_path


def test_writes_local_results_and_marks_upload_todo(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    github_output = tmp_path / "gh-output"
    result = run(
        project,
        NULLCASE_RESULTS_PATH="out.jsonl",
        NULLCASE_PYTEST_ARGS="-p no:randomly -q",
        GITHUB_OUTPUT=str(github_output),
    )

    assert result.returncode == 1  # pytest's exit code: one test failed
    records = [json.loads(line) for line in (project / "out.jsonl").read_text().splitlines()]
    assert {(r["nodeid"], r["outcome"]) for r in records} == {
        ("test_sample.py::test_ok", "passed"),
        ("test_sample.py::test_bad", "failed"),
    }
    assert "::notice title=NullCase::Upload not implemented yet (TODO)" in result.stdout
    assert github_output.read_text() == f"results-path={project / 'out.jsonl'}\n"


def test_exit_code_is_zero_when_tests_pass(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    result = run(project, NULLCASE_PYTEST_ARGS="-k test_ok")
    assert result.returncode == 0
    assert (project / "nullcase-results.jsonl").exists()


def test_warns_when_pytest_writes_nothing(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    for args in ["--collect-only", "--no-such-option"]:
        result = run(project, NULLCASE_PYTEST_ARGS=args)
        assert "::warning title=NullCase::pytest wrote no results" in result.stdout
        assert "Upload not implemented" not in result.stdout


def test_rejects_bad_settings_before_running_pytest(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    for env in [{"NULLCASE_DIAGNOSE": "sometimes"}, {"NULLCASE_MAX_DIAGNOSES": "0"}]:
        result = run(project, **env)
        assert result.returncode == 1
        assert "NullCase:" in result.stderr
        assert not (project / "nullcase-results.jsonl").exists()


def test_settings_defaults_and_explicit_tests() -> None:
    settings = read_settings({"NULLCASE_DIAGNOSE_TESTS": "a.py::x\n\n  b.py::y[1,2]  \n"})
    assert settings == Settings(
        diagnose_failed=False,
        explicit=("a.py::x", "b.py::y[1,2]"),
        max_diagnoses=3,
        budget_s=900.0,
        baseline_runs=20,
        runs=20,
        sandbox_source="",
    )
    assert read_settings({"NULLCASE_DIAGNOSE": "Failed"}).diagnose_failed


def test_select_targets_puts_explicit_first_dedupes_and_caps() -> None:
    records = [
        {"nodeid": "t.py::a", "outcome": "failed"},
        {"nodeid": "t.py::b", "outcome": "passed"},
        {"nodeid": "t.py::c", "outcome": "error"},
        {"nodeid": "t.py::d", "outcome": "failed"},
    ]
    settings = read_settings({"NULLCASE_DIAGNOSE": "failed", "NULLCASE_DIAGNOSE_TESTS": "t.py::c"})
    assert select_targets(records, settings) == ["t.py::c", "t.py::a", "t.py::d"]
    capped = read_settings({"NULLCASE_DIAGNOSE": "failed", "NULLCASE_MAX_DIAGNOSES": "1"})
    assert select_targets(records, capped) == ["t.py::a"]
    assert select_targets(records, read_settings({})) == []


def order_report(project: Path, python: str) -> dict[str, object]:
    nodeid = "tests/test_x.py::test_y"
    target = Target(project, nodeid, python)
    spec = plan(nodeid, 1, 1, ["order"])[1]["order"][0]
    report = BatteryReport(
        target,
        Rate(0, 20),
        {"order": Rate(16, 20), "hash_seed": Rate(0, 20)},
        BatteryDiagnosis("order_dependent", ("order",)),
        Repro(repro_command(target, spec), spec.setting, 3, 3),
    )
    return report_to_dict(report)


def test_summary_shows_rates_diagnosis_and_a_portable_repro(tmp_path: Path) -> None:
    python = str(tmp_path / "some env" / "python")
    report = order_report(tmp_path / "my project", python)
    summary = render_summary([Diagnosis("tests/test_x.py::test_y", "diagnosed", report)], python)

    assert "### `tests/test_x.py::test_y`" in summary
    assert "**order_dependent**: fails when the test order changes" in summary
    assert "| order | 20 | 16 | 0.80 | [0.58, 0.92] | differs from baseline |" in summary
    assert "| hash_seed | 20 | 0 | 0.00 | [0.00, 0.16] |  |" in summary
    assert "failed 3/3 replays" in summary
    repro = summary.split("```bash\n", 1)[1].split("\n```", 1)[0]
    assert repro.startswith("PYTHONHASHSEED=0 TZ=UTC python -m pytest ")
    assert "--randomly-seed=" in repro
    assert "my project" not in repro and "some env" not in repro


def test_summary_explains_undiagnosed_tests() -> None:
    summary = render_summary([Diagnosis("t.py::a", "skipped", message="time budget used up")], "")
    assert "Not diagnosed: time budget used up" in summary


def test_annotations_escape_text_and_pick_a_level(tmp_path: Path) -> None:
    report = order_report(tmp_path, "python")
    line = annotation(Diagnosis("t.py::a[x,y]", "diagnosed", report), "sub dir/t.py")
    assert line.startswith("::warning file=sub dir/t.py,title=NullCase%3A order_dependent::")
    assert "order_dependent::t.py::a[x,y] fails when the test order changes;" in line
    quiet = annotation(Diagnosis("t.py::a", "error", message="50%\nbad"), None)
    assert quiet == "::notice title=NullCase::t.py::a not diagnosed: 50%25%0Abad"


def test_annotation_file_is_relative_to_the_workspace(tmp_path: Path) -> None:
    project = tmp_path / "service"
    assert annotation_file(project, "tests/t.py::a", str(tmp_path)) == "service/tests/t.py"
    assert annotation_file(project, "tests/t.py::a", str(tmp_path / "elsewhere")) is None
    assert annotation_file(project, "tests/t.py::a", None) is None


def test_diagnoses_an_order_dependent_test_end_to_end(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    for name in ("pyproject.toml", "test_registry.py"):
        (project / name).write_text((DIAGNOSE_FIXTURE / name).read_text(encoding="utf-8"))
    summary, output = tmp_path / "summary.md", tmp_path / "gh-output"
    result = run(
        project,
        NULLCASE_PYTEST_ARGS="-p no:randomly -q",
        NULLCASE_DIAGNOSE_TESTS="test_registry.py::test_first_registration_gets_id_1",
        NULLCASE_BASELINE_RUNS="10",
        NULLCASE_RUNS="10",
        GITHUB_STEP_SUMMARY=str(summary),
        GITHUB_OUTPUT=str(output),
        GITHUB_WORKSPACE=str(tmp_path),
    )

    assert result.returncode == 0, result.stdout + result.stderr  # passes in file order
    diagnoses = json.loads((project / "nullcase-diagnoses.json").read_text(encoding="utf-8"))
    assert [(d["status"], d["report"]["category"]) for d in diagnoses] == [
        ("diagnosed", "order_dependent")
    ]
    assert f"diagnoses-path={project / 'nullcase-diagnoses.json'}\n" in output.read_text()
    assert "**order_dependent**" in summary.read_text(encoding="utf-8")
    assert "::warning file=project/test_registry.py,title=NullCase%3A order_dependent::" in (
        result.stdout
    )

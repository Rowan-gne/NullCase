import json
import os
import subprocess
import sys
from pathlib import Path

ENTRYPOINT = Path(__file__).resolve().parents[1] / "entrypoint.py"

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

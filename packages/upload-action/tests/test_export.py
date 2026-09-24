import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "export_upload_action.py"


def export(dest: Path, repo: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(dest), repo], capture_output=True, text=True
    )


def test_exports_a_root_level_action_repo(tmp_path: Path) -> None:
    dest = tmp_path / "repo"
    result = export(dest, "someone/nullcase-upload-action")
    assert result.returncode == 0, result.stderr
    files = {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()}
    assert {
        "action.yml",
        "entrypoint.py",
        "LICENSE",
        "README.md",
        ".github/workflows/self-test.yml",
        "self-test/test_fixture.py",
        "self-test/check_results.py",
    } <= files
    assert not any("__pycache__" in f for f in files)
    readme = (dest / "README.md").read_text()
    assert "uses: someone/nullcase-upload-action@v0.1.0" in readme
    assert "{{REPO}}" not in readme


def test_refuses_non_empty_destination_and_bad_slug(tmp_path: Path) -> None:
    (tmp_path / "existing").write_text("x")
    assert export(tmp_path, "a/b").returncode == 1
    assert export(tmp_path / "new", "not a slug").returncode == 1

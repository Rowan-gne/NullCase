"""Install the built wheels into a fresh virtualenv and exercise them.

Usage: python scripts/smoke_test_dist.py DIST_DIR

Catches packaging mistakes the in-repo test suite can't see: missing files,
broken entry points, wrong dependency metadata. The wheels are installed by
path, so the nullcase-* packages can never be resolved from PyPI instead.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

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


def run(*cmd: str | Path, cwd: Path | None = None) -> str:
    result = subprocess.run(
        [str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise SystemExit(f"failed: {' '.join(map(str, cmd))}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    wheels = sorted(Path(argv[1]).resolve().glob("*.whl"))
    names = {w.name.split("-")[0] for w in wheels}
    expected = {"nullcase_pytest", "nullcase_retrieval", "nullcase_sandbox"}
    if names != expected:
        raise SystemExit(f"expected wheels for {sorted(expected)}, found {sorted(names)}")

    with tempfile.TemporaryDirectory(prefix="nullcase-smoke-") as tmp:
        root = Path(tmp)
        venv.create(root / "venv", with_pip=True)
        bin_dir = root / "venv" / ("Scripts" if sys.platform == "win32" else "bin")
        python = bin_dir / "python"
        run(python, "-m", "pip", "install", "--quiet", *wheels)

        run(bin_dir / "nullcase-battery", "--help")
        run(bin_dir / "nullcase-coverage", "--help")
        run(python, "-m", "nullcase_sandbox", "--help")
        run(python, "-c", "import nullcase_retrieval.retrieve")

        project = root / "project"
        project.mkdir()
        (project / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
        (project / "test_state.py").write_text(ORDER_DEPENDENT, encoding="utf-8")

        run(
            python,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:randomly",
            "--nullcase-results=r.jsonl",
            cwd=project,
        )
        records = (project / "r.jsonl").read_text(encoding="utf-8").splitlines()
        if len(records) != 4:
            raise SystemExit(f"plugin wrote {len(records)} records, expected 4")

        report = json.loads(
            run(
                bin_dir / "nullcase-battery",
                "--project",
                project,
                "--only",
                "order",
                "--baseline-runs",
                "10",
                "--runs",
                "15",
                "--json",
                "test_state.py::test_victim",
            )
        )
        if report["category"] != "order_dependent" or not report["repro"]:
            raise SystemExit(f"unexpected battery result: {report}")

    print(f"ok: {', '.join(w.name for w in wheels)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

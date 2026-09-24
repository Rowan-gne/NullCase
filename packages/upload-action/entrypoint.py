"""Entrypoint for the NullCase GitHub Action (docs/technical-guide.md §3.5).

Installs nullcase-pytest if it isn't importable, runs pytest with local JSON
Lines output, then passes the results to RemoteUploadSink. That sink is still
a stub (there is no backend yet), so the upload step only prints a notice.
Exits with pytest's exit code, so failing tests still fail the job.

Configured through environment variables (action.yml sets them from inputs):
  NULLCASE_PLUGIN_SOURCE  pip requirement or path for nullcase-pytest
  NULLCASE_PYTEST_ARGS    extra pytest arguments, shell-style quoted
  NULLCASE_RESULTS_PATH   results file (default nullcase-results.jsonl)
"""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


def ensure_plugin(source: str) -> None:
    if importlib.util.find_spec("nullcase_pytest") is not None:
        return
    if not source:
        sys.exit("nullcase-pytest is not installed and NULLCASE_PLUGIN_SOURCE is empty")
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", source], check=True)


def run_pytest(extra_args: list[str], results: Path) -> int:
    command = [sys.executable, "-m", "pytest", f"--nullcase-results={results}", *extra_args]
    return subprocess.run(command, check=False).returncode


def upload(results: Path) -> None:
    from nullcase_pytest.results import ResultRecord
    from nullcase_pytest.sinks import RemoteUploadSink

    sink = RemoteUploadSink()
    try:
        for line in results.read_text(encoding="utf-8").splitlines():
            sink.write(ResultRecord(**json.loads(line)))
        sink.close()
    except NotImplementedError:
        # TODO: real upload. Request a GitHub OIDC token (audience "nullcase",
        # workflow needs `permissions: id-token: write`) and send the results to
        # the NullCase API. Blocked until the backend exists.
        print(
            f"::notice title=NullCase::Upload not implemented yet (TODO); "
            f"results kept locally at {results}"
        )


def set_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def main() -> int:
    ensure_plugin(os.environ.get("NULLCASE_PLUGIN_SOURCE", ""))
    results = Path(os.environ.get("NULLCASE_RESULTS_PATH") or "nullcase-results.jsonl").resolve()
    exit_code = run_pytest(shlex.split(os.environ.get("NULLCASE_PYTEST_ARGS", "")), results)
    set_output("results-path", str(results))
    # The plugin creates the file at session start, so an empty file means no tests ran.
    if results.exists() and results.stat().st_size > 0:
        upload(results)
    else:
        print("::warning title=NullCase::pytest wrote no results; nothing to upload")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

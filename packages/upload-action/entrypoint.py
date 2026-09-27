"""Entrypoint for the NullCase GitHub Action.

Installs nullcase-pytest if it isn't importable, runs pytest with local JSON
Lines output, then passes the results to RemoteUploadSink. That sink is still
a stub until the hosted service exists, so the upload step only prints a notice.

Optionally diagnoses tests afterwards: installs nullcase-sandbox, runs its
experiment battery on each chosen test and writes the result to the job
summary, as annotations and as JSON. Exits with pytest's exit code, so failing
tests still fail the job and a diagnosis never changes the outcome.

action.yml runs this file with the interpreter that has the project's
dependencies, and configures it through environment variables:
  NULLCASE_PLUGIN_SOURCE     pip requirement or path for nullcase-pytest
  NULLCASE_PYTEST_ARGS       extra pytest arguments, shell-style quoted
  NULLCASE_RESULTS_PATH      results file (default nullcase-results.jsonl)
  NULLCASE_DIAGNOSE          "false" (default) or "failed": diagnose failed tests
  NULLCASE_DIAGNOSE_TESTS    node IDs to diagnose whatever their outcome, one per line
  NULLCASE_MAX_DIAGNOSES     most tests to diagnose (default 3)
  NULLCASE_DIAGNOSE_TIMEOUT_MINUTES  time budget for all diagnoses (default 15)
  NULLCASE_BASELINE_RUNS     battery baseline runs (default 20)
  NULLCASE_RUNS              battery runs per perturbation (default 20)
  NULLCASE_SANDBOX_SOURCE    pip requirement or path for nullcase-sandbox
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

FAILED_OUTCOMES = frozenset({"failed", "error"})

CATEGORY_TEXT = {
    "order_dependent": "fails when the test order changes; it depends on state other tests leave",
    "hash_order": "fails for some hash seeds; it relies on set or dict iteration order",
    "network": "fails without network access; it makes a real network call",
    "timezone": "fails in some timezones; it assumes the local timezone or date",
    "concurrency": "fails under parallel execution; it shares files, ports or other state",
    "timing": "fails intermittently with every factor pinned; likely timing or nondeterminism",
    "fails_consistently": "fails on every pinned run; likely broken, not flaky",
    "not_reproduced": "didn't fail on this runner under any condition",
}


@dataclass(frozen=True, slots=True)
class Settings:
    diagnose_failed: bool
    explicit: tuple[str, ...]
    max_diagnoses: int
    budget_s: float
    baseline_runs: int
    runs: int
    sandbox_source: str


@dataclass(frozen=True, slots=True)
class Diagnosis:
    nodeid: str
    status: str  # "diagnosed", "error" or "skipped"
    report: dict[str, Any] | None = None
    message: str = ""


def _positive_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    if not raw.isdigit() or int(raw) < 1:
        raise ValueError(f"{name} must be a positive integer, got {raw!r}")
    return int(raw)


def read_settings(env: Mapping[str, str]) -> Settings:
    mode = env.get("NULLCASE_DIAGNOSE", "").strip().lower() or "false"
    if mode not in ("false", "failed"):
        raise ValueError(f"diagnose must be 'false' or 'failed', got {mode!r}")
    explicit = env.get("NULLCASE_DIAGNOSE_TESTS", "")
    return Settings(
        diagnose_failed=mode == "failed",
        explicit=tuple(line.strip() for line in explicit.splitlines() if line.strip()),
        max_diagnoses=_positive_int(env, "NULLCASE_MAX_DIAGNOSES", 3),
        budget_s=60.0 * _positive_int(env, "NULLCASE_DIAGNOSE_TIMEOUT_MINUTES", 15),
        baseline_runs=_positive_int(env, "NULLCASE_BASELINE_RUNS", 20),
        runs=_positive_int(env, "NULLCASE_RUNS", 20),
        sandbox_source=env.get("NULLCASE_SANDBOX_SOURCE", "").strip(),
    )


def pip_install(*args: str) -> None:
    """Install into this interpreter with pip, or with uv when it has no pip (uv venvs)."""
    if importlib.util.find_spec("pip") is not None:
        command = [sys.executable, "-m", "pip", "install", "--quiet", *args]
    elif uv := shutil.which("uv"):
        command = [uv, "pip", "install", "--quiet", "--python", sys.executable, *args]
    else:
        sys.exit(f"NullCase: {sys.executable} has no pip and uv isn't on PATH")
    subprocess.run(command, check=True)


def ensure_plugin(source: str) -> None:
    if importlib.util.find_spec("nullcase_pytest") is not None:
        return
    if not source:
        sys.exit("nullcase-pytest is not installed and NULLCASE_PLUGIN_SOURCE is empty")
    pip_install(source)


def ensure_sandbox(source: str, scratch: Path) -> None:
    """Install nullcase-sandbox without letting pip change the installed pytest."""
    if importlib.util.find_spec("nullcase_sandbox") is not None:
        return
    if not source:
        sys.exit("nullcase-sandbox is not installed and NULLCASE_SANDBOX_SOURCE is empty")
    try:
        pin = f"pytest=={importlib.metadata.version('pytest')}\n"
    except importlib.metadata.PackageNotFoundError:
        pip_install(source)
        return
    constraints = scratch / "constraints.txt"
    constraints.write_text(pin, encoding="utf-8")
    pip_install("-c", str(constraints), source)


def run_pytest(extra_args: list[str], results: Path) -> int:
    command = [sys.executable, "-m", "pytest", f"--nullcase-results={results}", *extra_args]
    return subprocess.run(command, check=False).returncode


def read_records(results: Path) -> list[dict[str, Any]]:
    lines = results.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def upload(results: Path) -> None:
    from nullcase_pytest.results import ResultRecord
    from nullcase_pytest.sinks import RemoteUploadSink

    sink = RemoteUploadSink()
    try:
        for line in results.read_text(encoding="utf-8").splitlines():
            sink.write(ResultRecord(**json.loads(line)))
        sink.close()
    except NotImplementedError:
        # TODO: real upload, once the hosted service exists.
        print(
            f"::notice title=NullCase::Upload not implemented yet (TODO); "
            f"results kept locally at {results}"
        )


def select_targets(records: Sequence[Mapping[str, Any]], settings: Settings) -> list[str]:
    """Explicit node IDs first, then failed tests if requested; deduplicated and capped."""
    targets = list(settings.explicit)
    if settings.diagnose_failed:
        targets += [str(r["nodeid"]) for r in records if r["outcome"] in FAILED_OUTCOMES]
    return list(dict.fromkeys(targets))[: settings.max_diagnoses]


def run_diagnoses(targets: Sequence[str], settings: Settings, project: Path) -> list[Diagnosis]:
    deadline = time.monotonic() + settings.budget_s
    diagnoses: list[Diagnosis] = []
    for nodeid in targets:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            diagnoses.append(Diagnosis(nodeid, "skipped", message="time budget used up"))
            continue
        command = [
            *(sys.executable, "-m", "nullcase_sandbox", "--project", str(project), "--json"),
            *("--baseline-runs", str(settings.baseline_runs), "--runs", str(settings.runs)),
            nodeid,
        ]
        print(f"::group::NullCase: diagnosing {nodeid}", flush=True)
        try:
            result = subprocess.run(
                command,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=remaining,
                check=False,
            )
        except subprocess.TimeoutExpired:
            diagnoses.append(Diagnosis(nodeid, "skipped", message="time budget used up"))
        else:
            print(result.stderr, end="", flush=True)
            last = (result.stderr.strip().splitlines() or ["no output"])[-1]
            try:
                report = json.loads(result.stdout) if result.returncode == 0 else None
            except json.JSONDecodeError:
                report, last = None, "the battery's output wasn't JSON"
            if report is None:
                diagnoses.append(Diagnosis(nodeid, "error", message=last))
            else:
                diagnoses.append(Diagnosis(nodeid, "diagnosed", report))
        finally:
            print("::endgroup::", flush=True)
    return diagnoses


def local_repro(command: str, project: str, python: str) -> str:
    """The battery's repro command without the runner's absolute paths."""
    command = command.removeprefix(f"cd {shlex.quote(project)} && ")
    return command.replace(f"{shlex.quote(python)} -m pytest", "python -m pytest", 1)


def _row(name: str, rate: Mapping[str, Any], note: str) -> str:
    low, high = rate["interval"]
    fraction = rate["failures"] / rate["runs"]
    return (
        f"| {name} | {rate['runs']} | {rate['failures']} | {fraction:.2f} "
        f"| [{low:.2f}, {high:.2f}] | {note} |"
    )


def render_summary(diagnoses: Sequence[Diagnosis], python: str) -> str:
    lines = ["## NullCase diagnosis", ""]
    for diagnosis in diagnoses:
        lines += [f"### `{diagnosis.nodeid}`", ""]
        report = diagnosis.report
        if report is None:
            lines += [f"Not diagnosed: {diagnosis.message}", ""]
            continue
        category = report["category"]
        lines += [f"**{category}**: {CATEGORY_TEXT.get(category, '')}.", ""]
        lines += [
            "| run set | runs | fails | rate | 95% Wilson CI | |",
            "|---|--:|--:|--:|---|---|",
        ]
        lines.append(_row("baseline", report["baseline"], ""))
        for name, rate in report["perturbations"].items():
            note = "differs from baseline" if name in report["significant"] else ""
            lines.append(_row(name, rate, note))
        lines.append("")
        if report["method"] == "deterministic_flip":
            lines += [
                f"Decided by replay: `{report['flip_setting']}` flipped the outcome every time.",
                "",
            ]
        repro = report["repro"]
        if repro:
            command = local_repro(repro["command"], report["project"], python)
            lines += [
                f"Repro command for bash, from the project directory (failed "
                f"{repro['confirmed_failures']}/{repro['confirm_runs']} replays):",
                "",
                "```bash",
                command,
                "```",
                "",
            ]
        else:
            lines += ["No repro command: no setting failed on every replay.", ""]
    return "\n".join(lines)


def escape_data(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_property(text: str) -> str:
    return escape_data(text).replace(":", "%3A").replace(",", "%2C")


def annotation_file(project: Path, nodeid: str, workspace: str | None) -> str | None:
    """The test file's path relative to the repository root, as annotations need it."""
    file = project / nodeid.split("::", 1)[0]
    if not workspace:
        return None
    try:
        return file.resolve().relative_to(Path(workspace).resolve()).as_posix()
    except ValueError:
        return None


def annotation(diagnosis: Diagnosis, file: str | None) -> str:
    report = diagnosis.report
    if report is None:
        text = f"{diagnosis.nodeid} not diagnosed: {diagnosis.message}"
        return f"::notice title=NullCase::{escape_data(text)}"
    category = report["category"]
    level = "notice" if category == "not_reproduced" else "warning"
    properties = f"title={escape_property(f'NullCase: {category}')}"
    if file:
        properties = f"file={escape_property(file)},{properties}"
    text = f"{diagnosis.nodeid} {CATEGORY_TEXT.get(category, category)}"
    return f"::{level} {properties}::{escape_data(text)}"


def diagnose(targets: Sequence[str], settings: Settings, project: Path, results: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="nullcase-") as scratch:
        ensure_sandbox(settings.sandbox_source, Path(scratch))
    diagnoses = run_diagnoses(targets, settings, project)

    out = results.with_name("nullcase-diagnoses.json")
    out.write_text(json.dumps([asdict(d) for d in diagnoses], indent=2), encoding="utf-8")
    set_output("diagnoses-path", str(out))

    summary = render_summary(diagnoses, sys.executable)
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as fh:
            fh.write(summary + "\n")
    else:
        print(summary)
    workspace = os.environ.get("GITHUB_WORKSPACE")
    for d in diagnoses:
        print(annotation(d, annotation_file(project, d.nodeid, workspace)), flush=True)


def set_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def main() -> int:
    # Workflow logs are UTF-8; Windows would otherwise write the ANSI code page,
    # and fail outright on characters it can't encode.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        settings = read_settings(os.environ)
    except ValueError as exc:
        sys.exit(f"NullCase: {exc}")
    ensure_plugin(os.environ.get("NULLCASE_PLUGIN_SOURCE", ""))
    results = Path(os.environ.get("NULLCASE_RESULTS_PATH") or "nullcase-results.jsonl").resolve()
    exit_code = run_pytest(shlex.split(os.environ.get("NULLCASE_PYTEST_ARGS", "")), results)
    set_output("results-path", str(results))
    # The plugin creates the file at session start, so an empty file means no tests ran.
    records: list[dict[str, Any]] = []
    if results.exists() and results.stat().st_size > 0:
        records = read_records(results)
        upload(results)
    else:
        print("::warning title=NullCase::pytest wrote no results; nothing to upload")

    targets = select_targets(records, settings)
    if targets:
        diagnose(targets, settings, Path.cwd(), results)
    elif settings.diagnose_failed:
        print("NullCase: no failed tests to diagnose")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

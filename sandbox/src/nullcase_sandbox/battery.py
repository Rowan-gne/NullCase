"""Plans and runs the experiment battery against one test (docs/technical-guide.md §3.7).

Every run is a fresh ``python -m pytest`` subprocess in the target project,
with results read back through the nullcase-pytest plugin. The baseline pins
every factor the perturbations vary (test order, hash seed, timezone, serial
execution, network allowed); each perturbation varies exactly one of them.
"""

from __future__ import annotations

import json
import os
import random
import shlex
import subprocess
import tempfile
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import get_args

from nullcase_sandbox.diagnosis import Diagnosis, PerturbationName, diagnose
from nullcase_sandbox.stats import Rate

PINNED_ENV: Mapping[str, str] = {"PYTHONHASHSEED": "0", "TZ": "UTC"}
COMMON_ARGS: tuple[str, ...] = ("-p", "no:cacheprovider", "-q")
NO_SHUFFLE: tuple[str, ...] = ("-p", "no:randomly")
# Extreme UTC offsets: at any time of day at least two of these are on a
# different calendar date from UTC. (Etc/GMT signs are inverted: GMT-14 is UTC+14.)
TIMEZONES: tuple[str, ...] = ("Etc/GMT-14", "Etc/GMT-12", "Etc/GMT+12", "Etc/GMT+11")
PARALLEL_WORKERS = 4
# pytest-randomly orders tests by crc32(f"{seed}::{nodeid}"). CRC32 is linear,
# so consecutive seeds give correlated orders; spread seeds sample far more
# independent orders. Fixed generator seed keeps runs reproducible.
_SEED_SOURCE = random.Random(0)
ORDER_SEEDS: tuple[int, ...] = tuple(_SEED_SOURCE.randrange(2**32) for _ in range(1000))
ALL_PERTURBATIONS: tuple[PerturbationName, ...] = get_args(PerturbationName)
# Perturbations whose failing setting can be replayed exactly.
DETERMINISTIC: frozenset[PerturbationName] = frozenset(
    {"order", "hash_seed", "network_off", "timezone"}
)
REQUIRED_MODULES = ("pytest", "nullcase_pytest", "pytest_randomly", "pytest_socket", "xdist")
FAILED_OUTCOMES = frozenset({"failed", "error"})


class BatteryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RunSpec:
    setting: str
    pytest_args: tuple[str, ...]
    env: Mapping[str, str] = field(default_factory=lambda: dict(PINNED_ENV))


@dataclass(frozen=True, slots=True)
class Target:
    project: Path
    nodeid: str
    python: str

    @property
    def file(self) -> str:
        return self.nodeid.split("::", 1)[0]


def plan(
    nodeid: str,
    baseline_runs: int,
    runs: int,
    perturbations: Collection[PerturbationName] = ALL_PERTURBATIONS,
) -> tuple[list[RunSpec], dict[PerturbationName, list[RunSpec]]]:
    file = nodeid.split("::", 1)[0]
    isolated = (*NO_SHUFFLE, nodeid)
    baseline = [RunSpec("pinned", isolated) for _ in range(baseline_runs)]
    builders: dict[PerturbationName, Callable[[int], RunSpec]] = {
        "order": lambda i: RunSpec(
            f"--randomly-seed={ORDER_SEEDS[i % len(ORDER_SEEDS)]}",
            (f"--randomly-seed={ORDER_SEEDS[i % len(ORDER_SEEDS)]}", file),
        ),
        "hash_seed": lambda i: RunSpec(
            f"PYTHONHASHSEED={i + 1}", isolated, {**PINNED_ENV, "PYTHONHASHSEED": str(i + 1)}
        ),
        "network_off": lambda i: RunSpec("--disable-socket", ("--disable-socket", *isolated)),
        "timezone": lambda i: RunSpec(
            f"TZ={TIMEZONES[i % len(TIMEZONES)]}",
            isolated,
            {**PINNED_ENV, "TZ": TIMEZONES[i % len(TIMEZONES)]},
        ),
        "parallel": lambda i: RunSpec(
            f"-n {PARALLEL_WORKERS}", (*NO_SHUFFLE, "-n", str(PARALLEL_WORKERS), file)
        ),
    }
    return baseline, {name: [builders[name](i) for i in range(runs)] for name in perturbations}


def command(target: Target, spec: RunSpec, extra_args: tuple[str, ...] = ()) -> list[str]:
    return [target.python, "-m", "pytest", *COMMON_ARGS, *spec.pytest_args, *extra_args]


def repro_command(target: Target, spec: RunSpec) -> str:
    """A shell command that replays ``spec`` from any directory."""
    env = " ".join(f"{k}={shlex.quote(v)}" for k, v in sorted(spec.env.items()))
    return f"cd {shlex.quote(str(target.project))} && {env} {shlex.join(command(target, spec))}"


def run_once(target: Target, spec: RunSpec, timeout_s: float) -> str | None:
    """Run ``spec`` once and return the target test's outcome, or None if it didn't report."""
    with tempfile.TemporaryDirectory(prefix="nullcase-") as tmp:
        results = Path(tmp) / "results.jsonl"
        try:
            subprocess.run(
                command(target, spec, (f"--nullcase-results={results}",)),
                cwd=target.project,
                env={**os.environ, **spec.env},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None
        if not results.exists():
            return None
        return _outcome_for(results, target.nodeid)


def _outcome_for(results: Path, nodeid: str) -> str | None:
    for line in results.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record["nodeid"] == nodeid:
            return str(record["outcome"])
    return None


def _failed(outcome: str | None) -> bool:
    # A missing result (timeout, crash, collection error) counts as a failure.
    return outcome is None or outcome in FAILED_OUTCOMES


@dataclass(frozen=True, slots=True)
class Repro:
    command: str
    setting: str
    confirmed_failures: int
    confirm_runs: int


@dataclass(frozen=True, slots=True)
class BatteryReport:
    target: Target
    baseline: Rate
    perturbations: dict[PerturbationName, Rate]
    diagnosis: Diagnosis
    repro: Repro | None


def check_environment(python: str) -> None:
    probe = f"import {', '.join(REQUIRED_MODULES)}"
    result = subprocess.run([python, "-c", probe], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise BatteryError(
            f"{python} is missing battery dependencies ({', '.join(REQUIRED_MODULES)}): "
            + result.stderr.strip().splitlines()[-1]
        )


def run_battery(
    target: Target,
    *,
    baseline_runs: int = 20,
    runs: int = 20,
    confirm_runs: int = 3,
    perturbations: Collection[PerturbationName] = ALL_PERTURBATIONS,
    timeout_s: float = 120.0,
    progress: Callable[[str], None] = lambda _: None,
) -> BatteryReport:
    check_environment(target.python)
    baseline_specs, perturbation_specs = plan(target.nodeid, baseline_runs, runs, perturbations)

    progress("baseline")
    baseline_outcomes = [run_once(target, spec, timeout_s) for spec in baseline_specs]
    if all(outcome is None for outcome in baseline_outcomes):
        raise BatteryError(
            f"{target.nodeid!r} produced no result in any baseline run. Check that the node ID"
            " is relative to the project's pytest rootdir and that the project's tests run."
        )
    baseline = Rate(sum(map(_failed, baseline_outcomes)), len(baseline_outcomes))

    failing_specs: dict[PerturbationName, list[RunSpec]] = {}
    rates: dict[PerturbationName, Rate] = {}
    for name, specs in perturbation_specs.items():
        progress(name)
        failed = [_failed(run_once(target, spec, timeout_s)) for spec in specs]
        rates[name] = Rate(sum(failed), len(failed))
        failing_specs[name] = [spec for spec, f in zip(specs, failed, strict=True) if f]

    diagnosis = diagnose(baseline, rates)
    candidates: list[RunSpec] = []
    if diagnosis.significant and diagnosis.significant[0] in DETERMINISTIC:
        candidates = _distinct_settings(failing_specs[diagnosis.significant[0]])[:3]
    elif diagnosis.category == "fails_consistently":
        candidates = baseline_specs[:1]

    repro = None
    for spec in candidates:
        progress(f"confirming {spec.setting}")
        confirmed = sum(_failed(run_once(target, spec, timeout_s)) for _ in range(confirm_runs))
        if confirmed == confirm_runs:
            repro = Repro(repro_command(target, spec), spec.setting, confirmed, confirm_runs)
            break
    return BatteryReport(target, baseline, rates, diagnosis, repro)


def _distinct_settings(specs: list[RunSpec]) -> list[RunSpec]:
    seen: dict[str, RunSpec] = {}
    for spec in specs:
        seen.setdefault(spec.setting, spec)
    return list(seen.values())

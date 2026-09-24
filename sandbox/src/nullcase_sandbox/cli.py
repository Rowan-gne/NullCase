"""Command-line entry point: ``nullcase-battery [--project DIR] NODEID``."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from nullcase_sandbox.battery import (
    ALL_PERTURBATIONS,
    BatteryError,
    BatteryReport,
    Target,
    run_battery,
)
from nullcase_sandbox.stats import Rate, differs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nullcase-battery", description="Diagnose why a flaky pytest test fails."
    )
    parser.add_argument("nodeid", help="test node ID, relative to the project's pytest rootdir")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="default: cwd")
    parser.add_argument(
        "--python", default=sys.executable, help="interpreter with the project's deps installed"
    )
    parser.add_argument("--baseline-runs", type=int, default=20)
    parser.add_argument("--runs", type=int, default=20, help="runs per perturbation")
    parser.add_argument(
        "--only",
        nargs="+",
        choices=ALL_PERTURBATIONS,
        default=list(ALL_PERTURBATIONS),
        help="run only these perturbations",
    )
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    target = Target(args.project.resolve(), args.nodeid, args.python)
    try:
        report = run_battery(
            target,
            baseline_runs=args.baseline_runs,
            runs=args.runs,
            perturbations=args.only,
            progress=lambda step: print(f"… {step}", file=sys.stderr, flush=True),
        )
    except BatteryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report_to_dict(report), indent=2) if args.json else format_report(report))
    return 0


def _row(name: str, rate: Rate, note: str) -> str:
    low, high = rate.interval
    return (
        f"{name:<12} {rate.runs:>5} {rate.failures:>6} {rate.rate:>6.2f}"
        f"  [{low:.2f}, {high:.2f}]  {note}"
    )


def format_report(report: BatteryReport) -> str:
    lines = [
        f"target: {report.target.nodeid}",
        "",
        f"{'':<12} {'runs':>5} {'fails':>6} {'rate':>6}  95% Wilson CI",
        _row("baseline", report.baseline, ""),
    ]
    for name, rate in report.perturbations.items():
        note = "differs from baseline" if differs(rate, report.baseline) else ""
        lines.append(_row(name, rate, note))
    lines += ["", f"diagnosis: {report.diagnosis.category}"]
    if report.repro:
        r = report.repro
        lines.append(
            f"repro ({r.setting}, failed {r.confirmed_failures}/{r.confirm_runs} replays):"
        )
        lines.append(f"  {r.command}")
    else:
        lines.append("repro: none found (no deterministic failing setting)")
    return "\n".join(lines)


def report_to_dict(report: BatteryReport) -> dict[str, Any]:
    def rate(r: Rate) -> dict[str, Any]:
        return {"runs": r.runs, "failures": r.failures, "interval": list(r.interval)}

    return {
        "nodeid": report.target.nodeid,
        "project": str(report.target.project),
        "baseline": rate(report.baseline),
        "perturbations": {name: rate(r) for name, r in report.perturbations.items()},
        "category": report.diagnosis.category,
        "significant": list(report.diagnosis.significant),
        "repro": asdict(report.repro) if report.repro else None,
    }


if __name__ == "__main__":
    raise SystemExit(main())

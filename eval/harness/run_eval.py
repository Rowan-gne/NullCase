"""Run the battery against every seeded demo test and score the diagnoses.

Usage (from the repository root):
    uv run python eval/harness/run_eval.py [--runs N] [--baseline-runs N] [--out FILE]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nullcase_sandbox.battery import Target, run_battery
from nullcase_sandbox.cli import report_to_dict

HERE = Path(__file__).resolve().parent
DEMO_REPO = HERE.parent / "demo-repo"
LABELS_FILE = HERE / "labels.json"


def load_labels(path: Path = LABELS_FILE) -> dict[str, str]:
    labels: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
    return labels


def score(predictions: dict[str, str], labels: dict[str, str]) -> int:
    """Number of labelled tests whose predicted category matches the label."""
    return sum(predictions.get(nodeid) == label for nodeid, label in labels.items())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score the battery against the demo repo.")
    parser.add_argument("--baseline-runs", type=int, default=20)
    parser.add_argument("--runs", type=int, default=20, help="runs per perturbation")
    parser.add_argument("--out", type=Path, help="also write the full results as JSON")
    args = parser.parse_args(argv)

    labels = load_labels()
    predictions: dict[str, str] = {}
    reports: list[dict[str, Any]] = []
    for nodeid, label in labels.items():
        print(f"running battery: {nodeid}", file=sys.stderr, flush=True)
        report = run_battery(
            Target(DEMO_REPO, nodeid, sys.executable),
            baseline_runs=args.baseline_runs,
            runs=args.runs,
        )
        predictions[nodeid] = report.diagnosis.category
        reports.append({**report_to_dict(report), "label": label})

    width = max(map(len, labels))
    print(f"{'test':<{width}}  {'label':<16} {'predicted':<18} repro")
    for entry in reports:
        mark = "ok  " if entry["category"] == entry["label"] else "MISS"
        repro = "yes" if entry["repro"] else "no"
        print(
            f"{entry['nodeid']:<{width}}  {entry['label']:<16} {entry['category']:<18} {repro}"
            f"  {mark}"
        )
    correct = score(predictions, labels)
    print(f"\ncorrectly diagnosed: {correct} of {len(labels)}")

    if args.out:
        args.out.write_text(
            json.dumps(
                {
                    "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "baseline_runs": args.baseline_runs,
                    "runs_per_perturbation": args.runs,
                    "correct": correct,
                    "total": len(labels),
                    "results": reports,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

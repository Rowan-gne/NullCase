"""Turns failure rates into a category (docs/technical-guide.md §3.7, diagnosis rule)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from nullcase_sandbox.stats import Rate, differs

PerturbationName = Literal["order", "hash_seed", "network_off", "timezone", "parallel"]

Category = Literal[
    "order_dependent",
    "hash_order",
    "network",
    "timezone",
    "concurrency",
    "timing",
    "fails_consistently",
    "not_reproduced",
]

CATEGORY_FOR: dict[PerturbationName, Category] = {
    "order": "order_dependent",
    "hash_seed": "hash_order",
    "network_off": "network",
    "timezone": "timezone",
    "parallel": "concurrency",
}


Method = Literal["wilson_interval", "deterministic_flip", "baseline_only"]


@dataclass(frozen=True, slots=True)
class Diagnosis:
    category: Category
    # Perturbations whose rate differs significantly from baseline, largest effect first.
    significant: tuple[PerturbationName, ...]
    method: Method = "wilson_interval"
    # For "deterministic_flip": the setting whose replays all flipped the outcome.
    flip_setting: str | None = None


def diagnose(baseline: Rate, perturbations: Mapping[PerturbationName, Rate]) -> Diagnosis:
    """Pick the perturbation that moves the failure rate most, if any does significantly.

    "Significantly" means the perturbation's and the baseline's 95% Wilson
    intervals do not overlap, in either direction. With no significant
    perturbation, the baseline alone decides: intermittent failures in
    isolation point at timing/nondeterminism, failure on every run means the
    test is simply failing, and no failures means the battery could not
    reproduce the flake (likely CI-environment only).
    """

    def effect(name: PerturbationName) -> tuple[float, str]:
        return (-abs(perturbations[name].rate - baseline.rate), name)

    significant: list[PerturbationName] = sorted(
        (name for name, rate in perturbations.items() if differs(rate, baseline)), key=effect
    )
    if significant:
        return Diagnosis(CATEGORY_FOR[significant[0]], tuple(significant))
    if baseline.failures == baseline.runs:
        return Diagnosis("fails_consistently", (), "baseline_only")
    if baseline.failures > 0:
        return Diagnosis("timing", (), "baseline_only")
    return Diagnosis("not_reproduced", (), "baseline_only")


def flip_eligible(diagnosis: Diagnosis) -> bool:
    """Whether the deterministic-flip check applies: a constant baseline, no Wilson result."""
    return diagnosis.category in ("fails_consistently", "not_reproduced")


def is_confirmed_flip(baseline: Rate, replay_failures: int, replay_runs: int) -> bool:
    """True when the baseline never varied and every replay had the opposite outcome.

    This covers what the interval comparison can't: a factor whose effect is a
    fixed function of its setting, where the pinned baseline setting sits on
    the rare side (e.g. a hash-order test that fails under PYTHONHASHSEED=0
    and passes under only a few other seeds). Varying the setting then moves
    the rate too little for the intervals to separate, but replaying one
    setting shows the outcome is determined by it.
    """
    if replay_runs <= 0 or not 0 <= replay_failures <= replay_runs:
        return False
    if baseline.failures == 0:
        return replay_failures == replay_runs
    if baseline.failures == baseline.runs:
        return replay_failures == 0
    return False


def flipped(name: PerturbationName, setting: str) -> Diagnosis:
    return Diagnosis(CATEGORY_FOR[name], (), "deterministic_flip", setting)

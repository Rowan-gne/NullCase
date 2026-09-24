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


@dataclass(frozen=True, slots=True)
class Diagnosis:
    category: Category
    # Perturbations whose rate differs significantly from baseline, largest effect first.
    significant: tuple[PerturbationName, ...]


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
        return Diagnosis("fails_consistently", ())
    if baseline.failures > 0:
        return Diagnosis("timing", ())
    return Diagnosis("not_reproduced", ())

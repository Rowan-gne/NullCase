"""Failure-rate statistics."""

from __future__ import annotations

import math
from dataclasses import dataclass

Z_95 = 1.959963984540054


def wilson_interval(failures: int, runs: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (failures / runs)."""
    if runs <= 0:
        raise ValueError(f"runs must be positive, got {runs}")
    if not 0 <= failures <= runs:
        raise ValueError(f"failures must be in [0, {runs}], got {failures}")
    p = failures / runs
    z2 = z * z
    denom = 1 + z2 / runs
    centre = (p + z2 / (2 * runs)) / denom
    half = z * math.sqrt(p * (1 - p) / runs + z2 / (4 * runs * runs)) / denom
    low = 0.0 if failures == 0 else max(0.0, centre - half)
    high = 1.0 if failures == runs else min(1.0, centre + half)
    return low, high


@dataclass(frozen=True, slots=True)
class Rate:
    failures: int
    runs: int

    def __post_init__(self) -> None:
        wilson_interval(self.failures, self.runs)  # validates

    @property
    def rate(self) -> float:
        return self.failures / self.runs

    @property
    def interval(self) -> tuple[float, float]:
        return wilson_interval(self.failures, self.runs)


def differs(a: Rate, b: Rate) -> bool:
    """True when the two rates' 95% Wilson intervals do not overlap."""
    a_low, a_high = a.interval
    b_low, b_high = b.interval
    return a_low > b_high or b_low > a_high

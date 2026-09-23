"""The per-test result record the plugin emits."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

Outcome = Literal["passed", "failed", "skipped", "error", "xfailed", "xpassed"]


@dataclass(frozen=True, slots=True)
class ResultRecord:
    """One test's final result, with setup/call/teardown folded together."""

    nodeid: str
    file_path: str
    outcome: Outcome
    duration_s: float

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

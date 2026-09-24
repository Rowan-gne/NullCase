"""Rank existing tests as style examples for a target (docs/technical-guide.md §3.9)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from nullcase_retrieval.graph import ImportGraph, module_name

_NOISE = frozenset({"test", "tests", "src", "py"})


@dataclass(frozen=True, slots=True)
class Candidate:
    path: Path  # relative to the repository root
    score: float


def parse_target(root: Path, target: str) -> tuple[str, str | None]:
    """Split ``pkg.mod``, ``pkg.mod:func`` or ``path/to/mod.py[:func]`` into (module, function)."""
    spec, _, function = target.partition(":")
    if spec.endswith(".py"):
        spec = module_name((root / spec).resolve())
    return spec, function or None


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and t not in _NOISE}


def similarity(module: str, function: str | None, test_path: Path) -> float:
    """Token overlap between the target and a test's path, tie-broken by stem similarity."""
    target = _tokens(module.replace(".", " ") + " " + (function or ""))
    candidate = _tokens(" ".join(test_path.with_suffix("").parts))
    union = target | candidate
    jaccard = len(target & candidate) / len(union) if union else 0.0
    last = function or module.rpartition(".")[2]
    stem = test_path.stem.removeprefix("test_").removesuffix("_test")
    return round(jaccard + 0.01 * SequenceMatcher(None, last, stem).ratio(), 6)


def import_graph_candidates(root: Path, target: str) -> list[Candidate]:
    """Test files that import the target's module, best match first."""
    module, function = parse_target(root, target)
    graph = ImportGraph.build(root)
    ranked = [
        Candidate(m.path, similarity(module, function, m.path))
        for m in graph.importers_of(module)
        if m.is_test
    ]
    return sorted(ranked, key=lambda c: (-c.score, str(c.path)))


def embedding_candidates(root: Path, target: str, k: int) -> list[Candidate]:
    """Nearest-neighbour test functions by embedding. Not implemented.

    Planned design (docs/technical-guide.md §3.9, steps 3-4): embed test
    functions with a small local model via ``fastembed`` (e.g. a 384-dimension
    BGE-small variant), store them in a pgvector ``vector(384)`` column with an
    HNSW index, and query nearest neighbours of the target. That needs the
    backend's Postgres, which does not exist yet, so this only raises.
    """
    raise NotImplementedError(
        "Embedding fallback is not implemented yet; see docs/technical-guide.md §3.9."
    )


def find_example_tests(root: Path, target: str, k: int = 1) -> list[Candidate]:
    """Up to ``k`` example tests for ``target``.

    Import-graph candidates are used when there are at least ``k`` of them;
    otherwise this falls through to ``embedding_candidates``, which currently
    raises ``NotImplementedError``.
    """
    candidates = import_graph_candidates(root, target)
    if len(candidates) >= k:
        return candidates[:k]
    return embedding_candidates(root, target, k)

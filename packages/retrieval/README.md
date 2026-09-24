# nullcase-retrieval

Finds existing tests to use as style examples for a target module or function:
the import-graph half of §3.9 in
[docs/technical-guide.md](../../docs/technical-guide.md). Local only; it reads
the repository's files and needs no backend.

```python
from pathlib import Path
from nullcase_retrieval.retrieve import find_example_tests

find_example_tests(Path("."), "nullcase_sandbox.stats", k=2)
find_example_tests(Path("."), "sandbox/src/nullcase_sandbox/diagnosis.py:diagnose")
```

1. Parse every `.py` file with `ast` (skipping virtualenvs, hidden and build
   directories) and resolve absolute and relative imports into dotted names.
2. Candidates are test files (`test_*.py`, `*_test.py`) that import the
   target module or one of its submodules.
3. Rank by token overlap between the target (module path and function name)
   and the test's path, tie-broken by stem similarity.
4. If fewer than `k` candidates exist, fall back to `embedding_candidates`.
   **Not implemented:** it raises `NotImplementedError`. The planned pgvector
   and fastembed design needs the backend's database.

Limitation: only static imports count. A test that exercises a module
indirectly (for example through `pytester`, or by importing only its package)
is not found.

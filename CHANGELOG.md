# Changelog

## 0.1.0 — unreleased

First release of the public components. Nothing is on PyPI or the
GitHub Marketplace yet. Supports Python 3.11–3.14, all tested in CI.

### nullcase-pytest
- Records one result per test (node ID, file path, outcome, duration) to a
  local JSON Lines file with `--nullcase-results PATH`. Works under
  pytest-xdist.
- `RemoteUploadSink` and the quarantine list are stubs until a backend exists.

### nullcase-sandbox
- `nullcase-battery`: re-runs one test under baseline, order, hash-seed,
  network-off, timezone and parallel perturbations. It diagnoses by
  non-overlapping 95% Wilson intervals, plus a deterministic-flip check for
  constant baselines, and prints confirmed repro commands. There's also a
  Dockerfile.
- `nullcase-coverage`: reports whether one test executes given lines of a file.
- `--only` takes a comma-separated list (`--only order,hash_seed`). Previously
  it took space-separated names and swallowed a node ID placed after it.
- The Docker image is based on `python:3.14-slim`.

### nullcase-retrieval
- Ranks existing tests that import a target module, using an `ast` import
  graph. The embedding fallback is a stub.

### upload-action
- A composite GitHub Action that installs the plugin, runs pytest and keeps
  the results on the runner. The upload itself is a stub. CI runs it on a real
  GitHub Actions runner, installing the plugin from the repository checkout.

# Changelog

## 0.1.0 — unreleased

First release of the public components. Nothing is on PyPI or the
GitHub Marketplace yet. Supports Python 3.11–3.14 on Linux, macOS and
Windows.

### nullcase-pytest
- Records one result per test (node ID, file path, outcome, duration) to a
  local JSON Lines file with `--nullcase-results PATH`. Works under
  pytest-xdist.
- `file_path` uses forward slashes on Windows too, matching node IDs.
- `RemoteUploadSink` and the quarantine list are stubs until the hosted service
  exists.

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
- The timezone perturbation works on Windows. It now sets POSIX `TZ` values
  (`AAA-14` is UTC+14). Windows' C runtime misreads the IANA `Etc/GMT` names
  used before: on Windows 11, `Etc/GMT-14` and `Etc/GMT+12` both came out as
  UTC+1, so timezone runs didn't test the intended offsets. Offsets on Linux
  and macOS are unchanged.

### upload-action ("NullCase flaky test diagnosis")
- A composite GitHub Action that installs the plugin, runs pytest and keeps
  the results on the runner. The upload itself is a stub.
- Diagnose mode: `diagnose: failed` and `diagnose-tests` run the battery on
  chosen tests after pytest, and report each diagnosis in the job summary, as
  a file annotation and as JSON (`diagnoses-path`). Bounded by
  `max-diagnoses` and `diagnose-timeout-minutes`; the job's result is still
  pytest's.
- A `python` input for projects whose dependencies live in a virtualenv; uv
  venvs without pip are supported through `uv pip`.
- CI runs it on Linux, macOS and Windows runners, installing the packages
  from the repository checkout.

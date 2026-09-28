# nullcase-pytest

pytest plugin that records one result per test, for
[NullCase](https://github.com/Rowan-gne/NullCase).

## Usage

```bash
pytest --nullcase-results=results.jsonl
```

<p align="center">
  <img src="https://raw.githubusercontent.com/Rowan-gne/NullCase/main/assets/plugin.svg" width="880" alt="pytest run with --nullcase-results=results.jsonl on three demo tests; results.jsonl then holds one JSON record per test with its duration, file path, node ID and outcome.">
</p>

Without `--nullcase-results` the plugin does nothing. With it, each test
produces one JSON line:

```json
{"duration_s": 0.000155, "file_path": "tests/test_a.py", "nodeid": "tests/test_a.py::test_x", "outcome": "failed"}
```

`outcome` is one of `passed`, `failed`, `skipped`, `error` (setup or teardown
failed), `xfailed`, `xpassed`. `duration_s` is the sum of setup, call and
teardown. Under pytest-xdist only the controller writes the file.

## Status

- Implemented: per-test collection, local JSON Lines output (`LocalFileSink`).
- Not implemented: remote upload (`RemoteUploadSink` raises
  `NotImplementedError`), the quarantine list (always empty), CI metadata
  (run ID, attempt, SHA, runner OS), and collection errors (not recorded).

# nullcase-pytest

pytest plugin that records one result per test. Design: §3.5 of
[docs/technical-guide.md](../../docs/technical-guide.md).

## Usage

```bash
pytest --nullcase-results=results.jsonl
```

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

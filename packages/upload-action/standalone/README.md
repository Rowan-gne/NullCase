# NullCase test results

Runs pytest with the [nullcase-pytest](https://pypi.org/project/nullcase-pytest/)
plugin and records one JSON Lines result per test. It's part of
[NullCase](https://github.com/Rowan-gne/NullCase), which diagnoses flaky tests.

**Status: early-stage.** Results are written on the runner only. Uploading
them to NullCase isn't implemented yet (there is no backend), so the action
prints a notice where the upload will go. The job's exit status is pytest's.

```yaml
permissions:
  contents: read
steps:
  - uses: actions/checkout@v7
  - uses: actions/setup-python@v7
    with:
      python-version: "3.12"
  - run: pip install -r requirements.txt
  - id: nullcase
    uses: {{REPO}}@v0.1.0
    with:
      pytest-args: "-q"
  - uses: actions/upload-artifact@v7
    if: always()
    with:
      name: nullcase-results
      path: ${{ steps.nullcase.outputs.results-path }}
```

| Input | Default | |
|---|---|---|
| `pytest-args` | `""` | extra pytest arguments, shell-style quoting |
| `working-directory` | `.` | where pytest runs |
| `results-path` | `nullcase-results.jsonl` | relative to `working-directory` |
| `plugin-source` | `nullcase-pytest==0.1.0` | pip requirement for the plugin |

Output: `results-path` (absolute path of the results file).

Each line looks like:

```json
{"duration_s": 0.000155, "file_path": "tests/test_a.py", "nodeid": "tests/test_a.py::test_x", "outcome": "failed"}
```

This repository is generated from `packages/upload-action` in the NullCase
repo; make changes there.

## License

[MIT](LICENSE)

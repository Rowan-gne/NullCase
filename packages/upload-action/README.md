# upload-action

GitHub Action wrapper for `nullcase-pytest` (§3.5 of
[docs/technical-guide.md](https://github.com/Rowan-gne/NullCase/blob/main/docs/technical-guide.md)). It installs the
plugin, runs pytest with local JSON Lines output, then passes the results to
`RemoteUploadSink`.

**Upload is not implemented.** `RemoteUploadSink` is a stub because there is no
backend yet. The action prints a `::notice::` and leaves the results file on
the runner. The job's exit status is pytest's.

```yaml
permissions:
  contents: read
  # id-token: write   # will be needed for OIDC upload once it exists
steps:
  - uses: actions/checkout@v7
  - uses: actions/setup-python@v7
    with:
      python-version: "3.12"
  - run: pip install -r requirements.txt
  - id: nullcase
    uses: Rowan-gne/NullCase/packages/upload-action@main
    with:
      pytest-args: "-q"
      # Until nullcase-pytest 0.1.0 is on PyPI, point at the plugin in this repo:
      # plugin-source: git+https://github.com/Rowan-gne/NullCase#subdirectory=packages/pytest-plugin
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
| `plugin-source` | `nullcase-pytest==0.1.0` | pip requirement for the plugin (a version, path or URL) |

Output: `results-path` (absolute path of the results file).

## Stand-alone repository

The Marketplace requires `action.yml` at the root of its own public repository
(§11.2). `scripts/export_upload_action.py DEST OWNER/REPO` assembles that
layout from this directory and `standalone/`. It adds a Marketplace README and
a `self-test` workflow that runs the action on a real runner against a small
fixture suite. See [RELEASING.md](https://github.com/Rowan-gne/NullCase/blob/main/RELEASING.md).

## Verification status

- `entrypoint.py` has been run standalone in fresh virtualenvs against sample
  projects. It installed the plugin, wrote correct results and exited with
  pytest's code. Its tests are in `tests/`.
- The exported repository's self-test flow has been run locally, with the
  plugin installed from the built 0.1.0 wheel in place of PyPI.
- `action.yml` and the self-test workflow pass actionlint.
- **Runs on a real GitHub Actions runner in this repo's CI** (the `upload-action
  on a real runner` job), against the self-test fixture, with the plugin
  installed from the checkout.
- **Not yet verified:** the default `plugin-source` (installing
  `nullcase-pytest==0.1.0` from PyPI), because the plugin isn't published yet.
  The exported repo's `self-test` workflow will be the first run of that path.

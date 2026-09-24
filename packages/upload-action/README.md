# upload-action

GitHub Action wrapper for `nullcase-pytest` (§3.5 of
[docs/technical-guide.md](../../docs/technical-guide.md)). It installs the
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
| `plugin-source` | the plugin bundled in this repo | pip requirement for `nullcase-pytest` |

Output: `results-path` (absolute path of the results file).

## Verification status

- `entrypoint.py` has been run standalone in a fresh virtualenv against a
  sample project. It installed the plugin, wrote correct results and exited
  with pytest's code. Its tests are in `tests/`.
- `action.yml` passes actionlint, checked by linting a workflow that uses it.
- **Not verified on a real Actions runner.**
- Not publishable to the Marketplace from here: that requires `action.yml` at
  the root of its own public repository (§11.2).

# upload-action

The source of the **NullCase flaky test diagnosis** GitHub Action. It installs
`nullcase-pytest`, runs pytest with local JSON Lines output and passes the
results to `RemoteUploadSink`. With `diagnose: failed` or `diagnose-tests`, it
then installs `nullcase-sandbox`, runs the experiment battery on each chosen
test and writes the diagnosis to the job summary, as file annotations and as
JSON. The job's exit status is always pytest's.

<p align="center">
  <img src="../../assets/ci-annotation.svg" width="880" alt="The NullCase Action in a real CI run on Rowan-gne/nullcase-demo: pytest fails tests/test_registry.py::test_first_user_gets_id_1, the Action re-runs it under controlled perturbations, and the run gets a warning annotation titled NullCase: order_dependent.">
</p>

**Upload is not implemented.** `RemoteUploadSink` is a stub until the hosted
service exists. The action logs where the results file is and leaves it on the
runner.

User-facing documentation (usage, inputs, an example job summary and caveats)
is the Marketplace README in [standalone/README.md](standalone/README.md).
Until the packages are on PyPI, point the action at this checkout:

```yaml
  - id: nullcase
    uses: Rowan-gne/NullCase/packages/upload-action@main
    with:
      diagnose: failed
      plugin-source: git+https://github.com/Rowan-gne/NullCase#subdirectory=packages/pytest-plugin
      sandbox-source: git+https://github.com/Rowan-gne/NullCase#subdirectory=sandbox
```

## How it runs

`action.yml` runs `entrypoint.py` with the `python` input (default: `python`
on `PATH`), so everything, including pip installs, uses the interpreter that
has the project's dependencies. Installs use pip, or `uv pip` when that
interpreter has no pip. nullcase-sandbox is installed only after the main
pytest run, with a constraint that keeps the installed pytest version.

## Stand-alone repository

The Marketplace requires `action.yml` at the root of its own public repository.
`scripts/export_upload_action.py DEST OWNER/REPO` assembles that layout from
this directory and `standalone/`: the Marketplace README, and a `self-test`
workflow that runs the action on Linux, macOS and Windows against two fixture
suites, installing both packages from PyPI.

## Verification status

- Unit tests cover settings, target selection, summary rendering and
  annotation escaping; an end-to-end test diagnoses an order-dependent fixture
  (`tests/`).
- The exported repository's self-test was rehearsed locally on Windows 11 and
  on Linux (Docker, Python 3.12) on 2026-09-27: the action's exact `run` line,
  fresh virtualenvs, both packages installed from the built 0.1.0 wheels. Both
  steps passed, and the diagnose step reported `order_dependent` with a repro
  command. On Windows it also passed in a venv without pip, through `uv pip`.
- `action.yml` and both workflows pass actionlint.
- This repo's CI runs the action on real Ubuntu, macOS and Windows runners,
  including a diagnose step, with the packages installed from the checkout.
  All three passed, most recently on 2026-09-28 (commit `1b95df8`).
- **Not yet verified:** the default PyPI sources, because nothing is published
  yet. The exported repo's `self-test` workflow will be the first run of that
  path.

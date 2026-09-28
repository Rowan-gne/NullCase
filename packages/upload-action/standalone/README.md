# NullCase flaky test diagnosis

Finds out *why* a flaky pytest test is flaky, by controlled experiment, on your
own CI runner.

The action runs your pytest suite and records one result per test. With
diagnosis turned on, it then re-runs each chosen test many times, changing one
factor at a time: test order, hash seed, network access, timezone and
parallelism. A 95% Wilson score interval decides which factor changes the
failure rate. The result goes to the job summary, with a command that
reproduces the failure when one is confirmed.

Part of [NullCase](https://github.com/Rowan-gne/NullCase). **Early-stage:**
everything runs on the runner, and nothing is sent anywhere.

## Usage

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
      diagnose: failed
  - uses: actions/upload-artifact@v7
    if: always()
    with:
      name: nullcase
      path: |
        ${{ steps.nullcase.outputs.results-path }}
        ${{ steps.nullcase.outputs.diagnoses-path }}
```

The job passes or fails exactly as pytest does; diagnosis never changes it.

## Example job summary

A real run of this repository's self-test (Linux, Python 3.12, 2026-09-27). The
test registers a user in a module-level list and expects to be first, so it
passes alone and fails when another test runs before it:

> ### `test_registry.py::test_first_registration_gets_id_1`
>
> **order_dependent**: fails when the test order changes; it depends on state other tests leave.
>
> | run set | runs | fails | rate | 95% Wilson CI | |
> |---|--:|--:|--:|---|---|
> | baseline | 20 | 0 | 0.00 | [0.00, 0.16] |  |
> | order | 20 | 16 | 0.80 | [0.58, 0.92] | differs from baseline |
> | hash_seed | 20 | 0 | 0.00 | [0.00, 0.16] |  |
> | network_off | 20 | 0 | 0.00 | [0.00, 0.16] |  |
> | timezone | 20 | 0 | 0.00 | [0.00, 0.16] |  |
> | parallel | 20 | 0 | 0.00 | [0.00, 0.16] |  |
>
> Repro command for bash, from the project directory (failed 3/3 replays):
>
> ```bash
> PYTHONHASHSEED=0 TZ=UTC python -m pytest -p no:cacheprovider -q --randomly-seed=3626764237 test_registry.py
> ```

Each diagnosed test also gets an annotation on its file. Possible diagnoses:
`order_dependent`, `hash_order`, `network`, `timezone`, `concurrency`,
`timing`, `fails_consistently` (likely broken, not flaky) and `not_reproduced`
(didn't fail on the runner under any condition).

## Inputs

| Input | Default | |
|---|---|---|
| `pytest-args` | `""` | extra pytest arguments, shell-style quoting |
| `working-directory` | `.` | where pytest runs; for diagnosis, the pytest rootdir |
| `python` | `python` on `PATH` | interpreter with your dependencies, e.g. `.venv/bin/python` |
| `results-path` | `nullcase-results.jsonl` | relative to `working-directory` |
| `plugin-source` | `nullcase-pytest==0.1.0` | pip requirement for the plugin |
| `diagnose` | `false` | `failed` diagnoses tests that failed in this run |
| `diagnose-tests` | `""` | node IDs to diagnose whatever their outcome, one per line |
| `max-diagnoses` | `3` | most tests diagnosed per run |
| `diagnose-timeout-minutes` | `15` | no new diagnosis starts after this |
| `baseline-runs` | `20` | baseline runs per test |
| `runs` | `20` | runs per perturbation per test |
| `sandbox-source` | `nullcase-sandbox==0.1.0` | pip requirement, installed only when diagnosing |

Outputs: `results-path` (JSON Lines, one record per test) and `diagnoses-path`
(JSON, empty when nothing was diagnosed).

## Good to know

- **Cost.** One diagnosis is 120 separate pytest runs of one test at the
  default settings, plus a few confirmation replays. For the self-test above
  that took under a minute in local rehearsals; suites with slow start-up take
  longer. `max-diagnoses` and `diagnose-timeout-minutes` bound it.
- **Environment.** Diagnosis installs `nullcase-sandbox`, which brings
  `pytest-randomly`, `pytest-socket`, `pytest-xdist` and `coverage` into the
  same environment, without changing your pytest version. pytest-randomly
  shuffles test order in any later pytest step of the same job; add
  `-p no:randomly` there if that matters.
- **Scope.** The battery runs each test with your pytest configuration but not
  with `pytest-args`. Use a Python with pip, or a uv-managed venv with `uv` on
  `PATH`. Repro commands are for bash (Git Bash on Windows).
- **Security.** Diagnosis runs your tests over a hundred times. Only use it on
  code you'd already run in CI.
- **Uploading results to NullCase** isn't implemented yet; the action logs where
  the results file is, on the runner.

This repository is generated from `packages/upload-action` in the NullCase
repo; make changes there.

## License

[MIT](LICENSE)

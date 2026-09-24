# NullCase

NullCase diagnoses flaky pytest tests by controlled experiment. It re-runs a
test many times, varies one factor at a time (test order, hash seed, network,
timezone, parallelism), and reports which factor changes the failure rate,
with a command that reproduces the failure when one exists.

**Status: early-stage — these are the public components; the hosted product is
in private development.** Nothing here is released on PyPI or the GitHub
Marketplace yet.

Full design: [docs/technical-guide.md](docs/technical-guide.md). This repository
covers the pytest plugin, the experiment battery, the evaluation harness,
example-test retrieval and the upload action. The file layout in §6.2 of that guide describes an earlier single-repo plan and
does not apply here.

## What's implemented

| Component | Path | Implemented | Not yet |
|---|---|---|---|
| pytest plugin | [packages/pytest-plugin](packages/pytest-plugin) | per-test outcome, duration, file path and node ID written to a local JSON Lines file | upload to a backend (OIDC), quarantine list (stub returns empty), CI metadata |
| Experiment battery | [sandbox](sandbox) | baseline, order, hash-seed, network-off, timezone and parallel perturbations; Wilson-interval diagnosis; confirmed repro commands; single-test coverage check for target lines (`nullcase-coverage`); CLIs; Dockerfile | running on Fly Machines; coverage check not yet part of an acceptance gate |
| Evaluation harness | [eval](eval) | demo repo with six seeded flaky tests; harness that scores the battery against their labels | a published external flaky-test dataset |
| Upload GitHub Action | [packages/upload-action](packages/upload-action) | composite action that installs the plugin and runs pytest with local results | the upload itself (stub prints a TODO notice); not yet run on a real Actions runner |
| Example-test retrieval | [packages/retrieval](packages/retrieval) | `ast` import graph; tests that import a target module, ranked by name/path similarity | embedding fallback (stub raises `NotImplementedError`) |

## Requirements

Python 3.11+ and [uv](https://docs.astral.sh/uv/). Docker is optional.

```bash
uv sync
uv run pytest        # this repo's own tests
```

## Run the battery

```bash
uv run nullcase-battery --project path/to/project tests/test_x.py::test_y
```

The node ID must be relative to the project's pytest rootdir. By default the
battery runs 20 baseline runs plus 20 runs of each of the five perturbations;
change this with `--baseline-runs` and `--runs`. For Docker usage and details
of each perturbation, see [sandbox/README.md](sandbox/README.md).

Example, on one of the demo tests:

```bash
uv run nullcase-battery --project eval/demo-repo \
  tests/test_order.py::test_first_user_gets_id_1
```

## Run the eval harness

```bash
uv run python eval/harness/run_eval.py              # about 3–4 minutes
uv run python eval/harness/run_eval.py --out results.json
```

It runs the full battery against each of the six seeded tests in
[eval/demo-repo](eval/demo-repo), compares the predicted category with the
label in [eval/harness/labels.json](eval/harness/labels.json), and prints how
many were diagnosed correctly. The network test makes a real HTTP request, so
it needs internet access.

## Eval results

**5 of 6 seeded tests diagnosed correctly**, in each of two full runs on
2026-09-24 (macOS, Python 3.12, 20 baseline runs and 20 runs per perturbation).

| Seeded test | Label | Predicted | Repro printed |
|---|---|---|---|
| `test_first_user_gets_id_1` | order_dependent | order_dependent | yes |
| `test_unique_tags_keeps_first_seen_order` | hash_order | **fails_consistently** (miss) | yes (the pinned baseline command) |
| `test_example_dot_com_is_up` | network | network | yes |
| `test_invoice_is_dated_today` | timezone | timezone | yes |
| `test_export_report[acme]` | concurrency | concurrency | no (not deterministic) |
| `test_cache_warmup_finishes_quickly` | timing | timing | no (not deterministic) |

**Why the hash-order test is missed:** the baseline pins `PYTHONHASHSEED=0`,
and under that seed this test fails every run (20/20). Varying the seed
brought failures down to 15/20, but the two 95% Wilson intervals overlap
([0.84, 1.00] vs [0.53, 0.89]), so the rule doesn't count it as a change.
This is a known weakness of the rate-comparison rule when the pinned setting
happens to be a failing one.

**Limits of this number:** six hand-written tests, one per category, labelled
by the same author who wrote the battery. It checks that each perturbation
works end to end. It is not a measure of accuracy on real-world flaky tests.
The timezone result depends on the time of day the harness runs, and the
network test needs internet access.

## License

[MIT](LICENSE)

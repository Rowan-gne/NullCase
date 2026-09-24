# NullCase

[![CI](https://github.com/Rowan-gne/NullCase/actions/workflows/ci.yml/badge.svg)](https://github.com/Rowan-gne/NullCase/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Finds out *why* a flaky pytest test is flaky, by controlled experiment.**

A flaky test passes and fails on the same code. The usual fix is to re-run
it or skip it. NullCase re-runs the test many times, changes one factor at
a time, and uses statistics to report which factor changes the failure rate.
When it can, it also prints a command that reproduces the failure every time.

> **Status:** early-stage, runs locally. This repo holds the open-source
> parts. The hosted service is in private development. Nothing is published
> to PyPI or the GitHub Marketplace yet.

## Example output

A real run on one of the demo tests (Windows 11, 2026-09-24). Absolute paths
are shortened to `<demo-repo>` and `<python>`, and the repro command is
wrapped to fit a phone screen:

```text
target: tests/test_order.py::test_first_user_gets_id_1

              runs  fails   rate  95% Wilson CI
baseline        20      0   0.00  [0.00, 0.16]
order           20     16   0.80  [0.58, 0.92]  differs from baseline
hash_seed       20      0   0.00  [0.00, 0.16]
network_off     20      0   0.00  [0.00, 0.16]
timezone        20      0   0.00  [0.00, 0.16]
parallel        20      0   0.00  [0.00, 0.16]

diagnosis: order_dependent (wilson interval)
repro (--randomly-seed=3626764237, failed 3/3 replays):
  cd <demo-repo> && PYTHONHASHSEED=0 TZ=UTC \
    <python> -m pytest -p no:cacheprovider -q \
    --randomly-seed=3626764237 tests/test_order.py
```

The test passes on its own every time, fails 16 of 20 times when test order
is shuffled, and is otherwise unaffected. So the diagnosis is: it depends on
another test running first.

## How it works

1. **Baseline.** Run the test 20 times with everything pinned: fixed order,
   fixed hash seed, UTC, network on, one process.
2. **Perturb.** Run it 20 more times per factor, changing only that factor:
   test order, `PYTHONHASHSEED`, network off, timezone, parallel workers.
3. **Compare.** Compute a 95% Wilson score interval for each failure rate.
   A factor matters if its interval doesn't overlap the baseline's.
4. **Confirm.** Replay the failing setting 3 times. Print a repro command
   only if it fails all 3.

Each run is a fresh `pytest` subprocess. Outcomes are read back through the
project's own pytest plugin.

<details>
<summary>Edge case: the deterministic-flip check</summary>

Some factors act like a switch: the test fails for one hash seed and passes
for another, every time. If the pinned baseline happens to sit on the
failing side, 20/20 vs 15/20 isn't separable by intervals at 20 runs. When
the baseline never varied and no factor is significant, the battery replays
each setting that produced the opposite outcome 3 times; if every replay
flips, that factor is reported. Details in
[sandbox/README.md](sandbox/README.md).

</details>

## Results on the demo suite

**6 of 6** seeded flaky tests diagnosed correctly, in two full runs on
2026-09-24 (macOS, Python 3.12, 20 runs per condition).

| Seeded test is flaky because of | Diagnosed |
|---|---|
| test order | ✅ |
| hash seed (set ordering) | ✅ |
| network access | ✅ |
| timezone | ✅ |
| concurrency | ✅ |
| timing | ✅ |

**Read this number carefully.** The first version scored **5 of 6**: it
missed the hash-order test. The deterministic-flip check was added *after*
seeing that miss, so 6/6 shows the fix works on the case it targets. It
isn't fresh evidence of accuracy. These are six hand-written tests, one per
category, labelled by the same author who wrote the battery. They check that
each perturbation works end to end; they don't measure accuracy on
real-world flaky tests.

<details>
<summary>Per-test detail</summary>

| Test | Decided by | Repro? |
|---|---|---|
| `test_first_user_gets_id_1` | Wilson interval | yes |
| `test_unique_tags_keeps_first_seen_order` | deterministic flip | yes |
| `test_example_dot_com_is_up` | Wilson interval | yes |
| `test_invoice_is_dated_today` | Wilson interval | yes |
| `test_export_report[acme]` | Wilson interval | no |
| `test_cache_warmup_finishes_quickly` | baseline only | no |

Concurrency and timing failures aren't deterministic, so no repro command is
printed for them. In the first version, the hash-order test's pinned seed
failed 20/20 and varied seeds failed 15/20; the 95% intervals ([0.84, 1.00]
vs [0.53, 0.89]) overlap, so it was reported as `fails_consistently`. The
timezone result depends on the time of day the harness runs, and the network
test needs internet access.

</details>

## What's in this repo

| Component | What it does |
|---|---|
| [pytest plugin](packages/pytest-plugin) | Records each test's outcome and duration to JSON Lines |
| [Experiment battery](sandbox) | The runs, statistics, diagnosis and repro above; CLI and Dockerfile |
| [Eval harness](eval) | Six seeded flaky tests and a scorer |
| [Test retrieval](packages/retrieval) | Finds tests that import a given module, via an `ast` import graph |
| [Upload Action](packages/upload-action) | GitHub Action that runs pytest with the plugin |

<details>
<summary>Not built yet (stubs)</summary>

- Uploading results to a backend. The plugin writes local files only; the
  Action's upload step prints a TODO notice.
- The quarantine list (always empty).
- Retrieval's embedding fallback (raises `NotImplementedError`).
- Running the battery on remote sandbox VMs. It runs locally or in Docker.
- AI-generated fixes or tests. There is no LLM layer in this repo.
- The Upload Action hasn't run on a real Actions runner.

The full product design (backend, GitHub App, dashboard) is in
[docs/technical-guide.md](docs/technical-guide.md); only the pieces above
live here. The file layout in §6.2 of that guide describes an earlier
single-repo plan and doesn't apply to this repo.

</details>

## Engineering

- **Python 3.11+** in a [uv](https://docs.astral.sh/uv/) workspace of
  three packages.
- **60 tests**, including property-based tests with Hypothesis for the
  statistics and diagnosis logic, and pytest's `pytester` for the plugin.
- **Strict type checking** with pyright, plus ruff lint and format.
- **CI** runs all of the above on every push
  ([workflow](.github/workflows/ci.yml)).
- **Release pipeline** prepared for PyPI Trusted Publishing, not yet used
  ([RELEASING.md](RELEASING.md), [CHANGELOG.md](CHANGELOG.md)).
- Wilson intervals are implemented directly
  ([stats.py](sandbox/src/nullcase_sandbox/stats.py)), no stats library.

## Run it yourself

Needs Python 3.11+ and [uv](https://docs.astral.sh/uv/). Docker is optional.

```bash
uv sync
uv run pytest
```

Diagnose one test (about 2 minutes):

```bash
uv run nullcase-battery --project eval/demo-repo \
  tests/test_order.py::test_first_user_gets_id_1
```

<details>
<summary>More usage</summary>

The node ID must be relative to the project's pytest rootdir. By default
the battery runs 20 baseline runs plus 20 runs of each of the five
perturbations; change this with `--baseline-runs` and `--runs`. For Docker
usage and details of each perturbation, see
[sandbox/README.md](sandbox/README.md).

Score the battery against all six seeded tests (about 3–4 minutes; the
network test needs internet access):

```bash
uv run python eval/harness/run_eval.py
uv run python eval/harness/run_eval.py --out results.json
```

It compares each predicted category with the label in
[eval/harness/labels.json](eval/harness/labels.json) and prints how many
were diagnosed correctly.

</details>

## License

[MIT](LICENSE)

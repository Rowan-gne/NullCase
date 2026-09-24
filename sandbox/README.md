# nullcase-sandbox

The experiment battery from §3.7 of
[docs/technical-guide.md](../docs/technical-guide.md): re-run one test many
times under controlled perturbations and see which one moves its failure rate.

## How it works

Every run is a fresh `python -m pytest` subprocess in the target project;
the outcome is read back through the `nullcase-pytest` plugin.

| Run set | What varies | Everything else |
|---|---|---|
| `baseline` | nothing — the test alone, repeated | pinned |
| `order` | test order in the test's file, via `pytest-randomly --randomly-seed` | pinned |
| `hash_seed` | `PYTHONHASHSEED` (1, 2, 3, …) | pinned |
| `network_off` | sockets blocked via `pytest-socket --disable-socket` | pinned |
| `timezone` | `TZ` across UTC+14, UTC+12, UTC−12, UTC−11 | pinned |
| `parallel` | the test's file under `pytest-xdist -n 4` | pinned |

"Pinned" means: no shuffling, `PYTHONHASHSEED=0`, `TZ=UTC`, serial, network
allowed.

**Diagnosis.** A perturbation is significant when its 95% Wilson score
interval does not overlap the baseline's (either direction). The significant
perturbation with the largest rate change sets the category: `order_dependent`,
`hash_order`, `network`, `timezone` or `concurrency`. If none is significant,
the baseline decides: some failures → `timing`, all failures →
`fails_consistently`, none → `not_reproduced`.

**Repro.** For order, hash seed, timezone and network, the battery replays the
failing setting 3 times and prints the command only if it fails all 3. Parallel
and timing failures are not deterministic, so no repro is printed for them.

## Usage

```bash
uv run nullcase-battery --project path/to/project tests/test_x.py::test_y
```

Options: `--baseline-runs N` and `--runs N` (default 20 each), `--only order
hash_seed …`, `--python PATH` (an interpreter with the project's dependencies
plus this package installed), `--json`.

### Docker

```bash
docker build -f sandbox/Dockerfile -t nullcase-battery .    # from the repo root
docker run --rm --network none -v "$PWD/path/to/project:/repo:ro" \
  nullcase-battery tests/test_x.py::test_y
```

The image has only the battery and its pytest plugins; a project with its own
dependencies needs a derived image that installs them.

## Limitations

- With the baseline pinned at `PYTHONHASHSEED=0`, a hash-order test that
  happens to fail under seed 0 fails every baseline run, and varying the seed
  rarely moves the rate enough to be significant. It is then reported as
  `fails_consistently`.
- The timezone result depends on the time of day the battery runs.
- Under `--network none` the baseline itself has no network, so a
  network-dependent test fails every run rather than being diagnosed as
  `network`.
- Fly Machines orchestration (§3.6) is not implemented; this runs locally or
  in Docker only.

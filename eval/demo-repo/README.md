# demo-repo

A small service with one deliberately flaky test per category from §6.6 of
[docs/technical-guide.md](../../docs/technical-guide.md). The known root causes
are recorded in [../harness/labels.json](../harness/labels.json).

| Test | Category | Why it flakes |
|---|---|---|
| `tests/test_order.py::test_first_user_gets_id_1` | order-dependent | module-level registry; fails if another test registers first |
| `tests/test_hash.py::test_unique_tags_keeps_first_seen_order` | hash-order | asserts on `set` iteration order |
| `tests/test_network.py::test_example_dot_com_is_up` | network | real HTTP call |
| `tests/test_timezone.py::test_invoice_is_dated_today` | timezone | compares a UTC date with local "today" |
| `tests/test_concurrency.py::test_export_report[acme]` | concurrency | all cases share one temp file; collides under xdist |
| `tests/test_timing.py::test_cache_warmup_finishes_quickly` | timing | fixed sleep races a background thread |

Run the suite: `cd eval/demo-repo && uv run pytest`.

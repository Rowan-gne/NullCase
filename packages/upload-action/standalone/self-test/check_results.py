"""Fail unless the action wrote the expected result records."""

import json
import sys
from pathlib import Path

records = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
outcomes = {r["nodeid"]: r["outcome"] for r in records}
expected = {"test_fixture.py::test_passes": "passed", "test_fixture.py::test_skipped": "skipped"}
if outcomes != expected:
    sys.exit(f"unexpected results: {outcomes}")
print(f"ok: {len(records)} records")

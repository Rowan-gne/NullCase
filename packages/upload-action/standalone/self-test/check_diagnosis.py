"""Fail unless the action diagnosed one test with the expected category and a repro."""

import json
import sys
from pathlib import Path

diagnoses = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = sys.argv[2]
if len(diagnoses) != 1 or diagnoses[0]["status"] != "diagnosed":
    sys.exit(f"unexpected diagnoses: {diagnoses}")
report = diagnoses[0]["report"]
if report["category"] != expected or not report["repro"]:
    sys.exit(f"expected {expected} with a repro command, got {report}")
print(f"ok: {diagnoses[0]['nodeid']} -> {report['category']}")

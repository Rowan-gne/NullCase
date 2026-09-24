"""Report export to a fixed scratch file."""

import tempfile
import time
from pathlib import Path

REPORT_PATH = Path(tempfile.gettempdir()) / "demo-service-report.txt"


def export_report(customer: str, rows: list[str]) -> Path:
    REPORT_PATH.write_text(f"Report: {customer}\n" + "\n".join(rows), encoding="utf-8")
    _notify_billing(customer)
    return REPORT_PATH


def _notify_billing(customer: str) -> None:
    time.sleep(0.02)  # stands in for a network call to the billing service

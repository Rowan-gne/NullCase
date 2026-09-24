import pytest
from demo_service.reports import export_report

CUSTOMERS = ["acme", "globex", "initech", "umbrella", "hooli", "stark"]


@pytest.mark.parametrize("customer", CUSTOMERS)
def test_export_report(customer):
    path = export_report(customer, ["line 1", "line 2"])
    assert path.read_text(encoding="utf-8").startswith(f"Report: {customer}\n")

from datetime import date

from demo_service.billing import invoice_date


def test_invoice_is_dated_today():
    assert invoice_date() == date.today()
